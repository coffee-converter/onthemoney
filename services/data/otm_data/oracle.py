from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy import Engine, text


@dataclass
class CandidateRef:
    cand_id: str
    name: str
    party: str
    office_state: str
    district: str


@dataclass
class DonorTotal:
    name: str
    employer: str
    amount: Decimal
    state: str = ""


@dataclass
class CandidateFinance:
    receipts: Decimal
    individual_total: Decimal


@dataclass
class StateTotal:
    state: str
    amount: Decimal
    count: int


def resolve_candidate(engine: Engine, *, state: str, district: str,
                      election_yr: int = 2024) -> CandidateRef | None:
    # A district can have many candidates; resolve to the one with the most
    # itemized individual receipts on file (memo transactions excluded), so
    # "the representative" lands on the leading candidate rather than an
    # arbitrary minor filer.
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT c.cand_id, c.name, c.party, c.office_state, c.district "
            "FROM candidates c "
            "LEFT JOIN candidate_committee cc "
            "  ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "LEFT JOIN contributions ct "
            "  ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
            "WHERE c.office = 'H' AND c.office_state = :state "
            "  AND c.district = :district AND c.election_yr = :yr "
            "GROUP BY c.cand_id, c.name, c.party, c.office_state, c.district "
            "ORDER BY COALESCE(SUM(ct.amount), 0) DESC, c.cand_id "
            "LIMIT 1"
        ), {"state": state, "district": district, "yr": election_yr}).first()
    return CandidateRef(*row) if row else None


def committees_for_candidate(engine: Engine, cand_id: str, *,
                             election_yr: int = 2024) -> list[str]:
    with engine.connect() as conn:
        return list(conn.execute(text(
            "SELECT cmte_id FROM candidate_committee "
            "WHERE cand_id = :c AND election_yr = :yr ORDER BY cmte_id"
        ), {"c": cand_id, "yr": election_yr}).scalars().all())


def total_raised(engine: Engine, cand_id: str, *, election_yr: int = 2024) -> Decimal:
    with engine.connect() as conn:
        val = conn.execute(text(
            "SELECT COALESCE(SUM(ct.amount), 0) FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "AND COALESCE(ct.memo_cd, '') <> 'X'"
        ), {"c": cand_id, "yr": election_yr}).scalar()
    return Decimal(val)


def top_donors(engine: Engine, cand_id: str, *, election_yr: int = 2024,
               n: int = 10) -> list[DonorTotal]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT ct.name, COALESCE(ct.employer, '') AS employer, "
            "MAX(COALESCE(ct.state, '')) AS state, SUM(ct.amount) AS amt "
            "FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "AND COALESCE(ct.memo_cd, '') <> 'X' "
            "GROUP BY ct.name, COALESCE(ct.employer, '') "
            "ORDER BY amt DESC, ct.name ASC LIMIT :n"
        ), {"c": cand_id, "yr": election_yr, "n": n}).all()
    return [DonorTotal(name=r[0], employer=r[1], state=r[2], amount=Decimal(r[3]))
            for r in rows]


@dataclass
class CandidateSummary:
    cand_id: str
    name: str
    party: str
    itemized: Decimal
    receipts: Decimal | None
    individual_total: Decimal | None


def district_candidates(engine: Engine, *, state: str, district: str,
                        election_yr: int = 2024) -> list[CandidateSummary]:
    # Every House candidate in the district that has itemized receipts, ranked
    # the same way resolve_candidate ranks (by itemized individual receipts), so
    # the top of the roster is the default "the representative" candidate.
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT c.cand_id, c.name, c.party, "
            "COALESCE(SUM(ct.amount), 0) AS itemized, "
            "MAX(t.receipts) AS receipts, MAX(t.individual_total) AS individual_total "
            "FROM candidates c "
            "LEFT JOIN candidate_committee cc "
            "  ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "LEFT JOIN contributions ct "
            "  ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
            "LEFT JOIN candidate_totals t ON t.cand_id = c.cand_id AND t.cycle = :yr "
            "WHERE c.office = 'H' AND c.office_state = :state "
            "  AND c.district = :district AND c.election_yr = :yr "
            "GROUP BY c.cand_id, c.name, c.party "
            "HAVING COALESCE(SUM(ct.amount), 0) > 0 "
            "ORDER BY COALESCE(SUM(ct.amount), 0) DESC, c.cand_id"
        ), {"state": state, "district": district, "yr": election_yr}).all()
    return [
        CandidateSummary(
            cand_id=r[0], name=r[1], party=r[2], itemized=Decimal(r[3]),
            receipts=Decimal(r[4]) if r[4] is not None else None,
            individual_total=Decimal(r[5]) if r[5] is not None else None,
        )
        for r in rows
    ]


@dataclass
class StateFieldEntry:
    district: str
    cand_id: str
    name: str
    party: str
    itemized: Decimal


def state_field(engine: Engine, state: str, *,
                election_yr: int = 2024) -> list[StateFieldEntry]:
    # Each district's leading candidate (by itemized receipts) across a state -
    # the data behind a whole-state candidate map.
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT ON (district) district, cand_id, name, party, itemized "
            "FROM (SELECT c.district, c.cand_id, c.name, c.party, "
            "  COALESCE(SUM(ct.amount), 0) AS itemized FROM candidates c "
            "  LEFT JOIN candidate_committee cc "
            "    ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "  LEFT JOIN contributions ct "
            "    ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
            "  WHERE c.office = 'H' AND c.office_state = :state "
            "    AND c.election_yr = :yr "
            "  GROUP BY c.district, c.cand_id, c.name, c.party) t "
            "ORDER BY district, itemized DESC"
        ), {"state": state, "yr": election_yr}).all()
    return [StateFieldEntry(district=r[0], cand_id=r[1], name=r[2], party=r[3],
                            itemized=Decimal(r[4])) for r in rows]


@dataclass
class StateFunding:
    state: str
    total: Decimal


def state_totals(engine: Engine, *, election_yr: int = 2024) -> list[StateFunding]:
    # Total itemized individual receipts across every House candidate, summed by
    # state - the data behind a nationwide funding heat map.
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT c.office_state AS state, COALESCE(SUM(ct.amount), 0) AS total "
            "FROM candidates c "
            "  LEFT JOIN candidate_committee cc "
            "    ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "  LEFT JOIN contributions ct "
            "    ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
            "WHERE c.office = 'H' AND c.election_yr = :yr "
            "GROUP BY c.office_state "
            "ORDER BY total DESC"
        ), {"yr": election_yr}).all()
    return [StateFunding(state=r[0], total=Decimal(r[1])) for r in rows]


@dataclass
class CandidateMatch:
    cand_id: str
    name: str
    state: str
    district: str
    party: str
    itemized: Decimal


def search_candidates(engine: Engine, name: str, *, election_yr: int = 2024,
                      limit: int = 8) -> list[CandidateMatch]:
    # Ground a person's name to real FEC candidate rows (cand_id, state,
    # district), so the agent never guesses which district someone represents.
    # FEC names are "LAST, FIRST MIDDLE"; require every query token to appear.
    tokens = [t for t in name.replace(",", " ").split() if len(t) > 1]
    if not tokens:
        return []
    clauses = " AND ".join(f"c.name ILIKE :t{i}" for i in range(len(tokens)))
    params: dict = {f"t{i}": f"%{tok}%" for i, tok in enumerate(tokens)}
    params.update({"yr": election_yr, "lim": limit})
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT c.cand_id, c.name, c.office_state, c.district, c.party, "
            "  COALESCE(SUM(ct.amount), 0) AS itemized FROM candidates c "
            "  LEFT JOIN candidate_committee cc "
            "    ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "  LEFT JOIN contributions ct "
            "    ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
            "WHERE c.office = 'H' AND c.election_yr = :yr AND " + clauses + " "
            "GROUP BY c.cand_id, c.name, c.office_state, c.district, c.party "
            "ORDER BY itemized DESC LIMIT :lim"
        ), params).all()
    return [CandidateMatch(cand_id=r[0], name=r[1], state=r[2], district=r[3],
                           party=r[4], itemized=Decimal(r[5])) for r in rows]


@dataclass
class EmployerTotal:
    employer: str
    amount: Decimal
    count: int


@dataclass
class IndustryTotal:
    industry: str
    amount: Decimal
    count: int


# Heuristic employer -> industry buckets (keyword match on the employer string).
# Not an authoritative classification, but enough to surface funding composition.
_INDUSTRY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Retired / Not employed",
     ("RETIRED", "NOT EMPLOYED", "UNEMPLOYED", "HOMEMAKER", "SELF EMPLOYED",
      "SELF-EMPLOYED")),
    ("Technology",
     ("GOOGLE", "ALPHABET", "META", "FACEBOOK", "APPLE", "AMAZON", "MICROSOFT",
      "NVIDIA", "TESLA", "NETFLIX", "ORACLE", "SALESFORCE", "INTEL", "SOFTWARE",
      "TECHNOLOG", "SEMICONDUCTOR")),
    ("Finance",
     ("GOLDMAN", "MORGAN", "JPMORGAN", "CITADEL", "BLACKROCK", "BLACKSTONE",
      "BANK", "CAPITAL", "FINANCIAL", "INVESTMENT", "EQUITY", "SECURITIES",
      "WELLS FARGO", "CITI", "HEDGE", "VENTURE")),
    ("Law", ("LAW", "LLP", "ATTORNEY", "LEGAL")),
    ("Healthcare",
     ("HEALTH", "MEDICAL", "HOSPITAL", "PHARMA", "PFIZER", "MERCK", "KAISER",
      "UNITEDHEALTH", "PHYSICIAN", "CLINIC", "BIOTECH")),
    ("Energy",
     ("EXXON", "CHEVRON", "ENERGY", "PETROLEUM", "SOLAR", " OIL", "OIL ", "GAS ")),
    ("Real Estate",
     ("REALTY", "REAL ESTATE", "PROPERTIES", "REALTOR", "DEVELOPMENT")),
    ("Education", ("UNIVERSITY", "COLLEGE", "SCHOOL", "EDUCATION", "ACADEM")),
    ("Government / Public",
     ("CITY OF", "STATE OF", "COUNTY OF", "FEDERAL", "GOVERNMENT", "PUBLIC")),
]


def classify_industry(employer: str | None) -> str:
    e = (employer or "").strip().upper()
    if not e:
        return "Unlisted"
    for name, keywords in _INDUSTRY_RULES:
        if any(k in e for k in keywords):
            return name
    return "Other"


def top_employers(engine: Engine, cand_id: str, *, election_yr: int = 2024,
                  n: int = 10) -> list[EmployerTotal]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT COALESCE(NULLIF(TRIM(ct.employer), ''), '(unlisted)') AS emp, "
            "SUM(ct.amount) AS amt, COUNT(*) AS cnt FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "AND COALESCE(ct.memo_cd, '') <> 'X' "
            "GROUP BY COALESCE(NULLIF(TRIM(ct.employer), ''), '(unlisted)') "
            "ORDER BY amt DESC, emp ASC LIMIT :n"
        ), {"c": cand_id, "yr": election_yr, "n": n}).all()
    return [EmployerTotal(employer=r[0], amount=Decimal(r[1]), count=int(r[2]))
            for r in rows]


def industry_breakdown(engine: Engine, cand_id: str, *,
                       election_yr: int = 2024) -> list[IndustryTotal]:
    # Pull employer-level sums, then fold into industry buckets in Python.
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT COALESCE(ct.employer, '') AS emp, SUM(ct.amount) AS amt, "
            "COUNT(*) AS cnt FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "AND COALESCE(ct.memo_cd, '') <> 'X' "
            "GROUP BY COALESCE(ct.employer, '')"
        ), {"c": cand_id, "yr": election_yr}).all()
    agg: dict[str, list] = {}
    for emp, amt, cnt in rows:
        bucket = agg.setdefault(classify_industry(emp), [Decimal(0), 0])
        bucket[0] += Decimal(amt)
        bucket[1] += int(cnt)
    out = [IndustryTotal(industry=k, amount=v[0], count=v[1]) for k, v in agg.items()]
    out.sort(key=lambda x: x.amount, reverse=True)
    return out


def candidate_finance(engine: Engine, cand_id: str, *,
                      election_yr: int = 2024) -> CandidateFinance | None:
    # Official FEC totals for the candidate (accurate headline figures), as
    # opposed to the itemized sum we compute from raw receipts.
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT receipts, individual_total FROM candidate_totals "
            "WHERE cand_id = :c AND cycle = :yr"
        ), {"c": cand_id, "yr": election_yr}).first()
    if row is None:
        return None
    return CandidateFinance(receipts=Decimal(row[0] or 0),
                            individual_total=Decimal(row[1] or 0))


def contributions_by_state(engine: Engine, cand_id: str, *,
                           election_yr: int = 2024) -> list[StateTotal]:
    # All itemized individual receipts grouped by contributor state (memo
    # excluded). Drives the map's geographic money-flow layer.
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT COALESCE(ct.state, '') AS st, SUM(ct.amount) AS amt, "
            "COUNT(*) AS cnt FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "AND COALESCE(ct.memo_cd, '') <> 'X' AND COALESCE(ct.state, '') <> '' "
            "GROUP BY COALESCE(ct.state, '') ORDER BY amt DESC"
        ), {"c": cand_id, "yr": election_yr}).all()
    return [StateTotal(state=r[0], amount=Decimal(r[1]), count=int(r[2]))
            for r in rows]

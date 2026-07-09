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


def candidate_by_id(engine: Engine, cand_id: str, *,
                    election_yr: int = 2024) -> CandidateRef | None:
    # Direct lookup of a candidate by FEC id - used when a tool already holds an
    # id (e.g. comparing two candidates the user named).
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT cand_id, name, party, office_state, district FROM candidates "
            "WHERE cand_id = :c AND election_yr = :yr LIMIT 1"
        ), {"c": cand_id, "yr": election_yr}).first()
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
class TimelineEntry:
    month: str
    amount: Decimal
    count: int


def funding_timeline(engine: Engine, cand_id: str, *,
                     election_yr: int = 2024) -> list[TimelineEntry]:
    # Itemized individual money by calendar month - the time dimension of a
    # candidate's fundraising (ramp, end-of-quarter surges, late money).
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT to_char(date_trunc('month', ct.transaction_dt), 'YYYY-MM') AS mon, "
            "  SUM(ct.amount) AS amt, COUNT(*) AS cnt FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "  AND COALESCE(ct.memo_cd, '') <> 'X' AND ct.transaction_dt IS NOT NULL "
            "GROUP BY mon ORDER BY mon"
        ), {"c": cand_id, "yr": election_yr}).all()
    return [TimelineEntry(month=r[0], amount=Decimal(r[1]), count=int(r[2]))
            for r in rows]


def donor_size_breakdown(engine: Engine, cand_id: str, *,
                         election_yr: int = 2024) -> dict:
    # Small-dollar vs large-dollar split. The real grassroots money is the
    # unitemized remainder (individual_total minus the itemized detail we hold),
    # so report that alongside itemized size buckets.
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT CASE WHEN ct.amount < 200 THEN 'under_200' "
            "  WHEN ct.amount < 1000 THEN '200_to_999' "
            "  WHEN ct.amount < 2900 THEN '1000_to_2899' "
            "  ELSE '2900_plus' END AS bucket, "
            "  SUM(ct.amount) AS amt, COUNT(*) AS cnt FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "  AND COALESCE(ct.memo_cd, '') <> 'X' GROUP BY bucket"
        ), {"c": cand_id, "yr": election_yr}).all()
    itemized_buckets = {r[0]: (Decimal(r[1]), int(r[2])) for r in rows}
    itemized_sum = sum((v[0] for v in itemized_buckets.values()), Decimal(0))
    fin = candidate_finance(engine, cand_id, election_yr=election_yr)
    individual = fin.individual_total if fin else Decimal(0)
    unitemized = individual - itemized_sum
    if unitemized < 0:
        unitemized = Decimal(0)
    small = unitemized + itemized_buckets.get("under_200", (Decimal(0), 0))[0]
    return {
        "individual_total": float(individual),
        "unitemized_small_dollar": float(unitemized),
        "small_dollar_share_pct": round(float(small / individual) * 100, 1)
        if individual else 0.0,
        "itemized_buckets": [
            {"range": k, "amount": float(v[0]), "count": v[1]}
            for k, v in sorted(itemized_buckets.items())
        ],
    }


@dataclass
class RankedCandidate:
    cand_id: str
    name: str
    state: str
    district: str
    party: str
    value: Decimal


def top_candidates(engine: Engine, *, metric: str = "itemized", limit: int = 10,
                   election_yr: int = 2024) -> list[RankedCandidate]:
    # Nationwide ranking of House candidates by a chosen money metric.
    base = ("SELECT c.cand_id, c.name, c.office_state, c.district, c.party, {val} AS v "
            "FROM candidates c ")
    if metric in ("receipts", "individual"):
        col = "receipts" if metric == "receipts" else "individual_total"
        sql = base.format(val=f"COALESCE(MAX(t.{col}), 0)") + (
            "LEFT JOIN candidate_totals t ON t.cand_id = c.cand_id AND t.cycle = :yr ")
    else:  # itemized
        sql = base.format(val="COALESCE(SUM(ct.amount), 0)") + (
            "LEFT JOIN candidate_committee cc "
            "  ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "LEFT JOIN contributions ct "
            "  ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' ")
    sql += ("WHERE c.office = 'H' AND c.election_yr = :yr "
            "GROUP BY c.cand_id, c.name, c.office_state, c.district, c.party "
            "ORDER BY v DESC LIMIT :lim")
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"yr": election_yr, "lim": limit}).all()
    return [RankedCandidate(cand_id=r[0], name=r[1], state=r[2], district=r[3],
                            party=r[4], value=Decimal(r[5])) for r in rows]


@dataclass
class RankedDistrict:
    state: str
    district: str
    cand_id: str
    name: str
    party: str
    value: Decimal


def rank_districts(engine: Engine, *, metric: str = "receipts", order: str = "asc",
                   limit: int = 10, election_yr: int = 2024) -> list[RankedDistrict]:
    # Rank every House district nationwide by its TOTAL funding (summed across
    # all candidates in the seat), ascending (least-funded first) or descending.
    # Value is the district total; the named candidate is the seat's top raiser.
    #
    # Summing the whole field, rather than a single "leading candidate", is what
    # makes "least-funded district" honest: a $0 minor or withdrawn filer can be
    # the nominal leader of a seat that actually raised millions, so per-leader
    # ranking surfaces false zeros. Districts with no reported money at all are
    # excluded from the ascending ("least") ranking as data gaps, not real seats.
    #
    # Default metric is 'receipts' (official FEC total raised), complete for
    # every filer. 'itemized' sums the itemized-contribution slice instead.
    direction = "ASC" if str(order).lower() == "asc" else "DESC"
    if metric == "itemized":
        cand = (
            "cand AS (SELECT c.office_state, c.district, c.cand_id, c.name, c.party, "
            "  COALESCE(SUM(ct.amount), 0) AS v FROM candidates c "
            "  LEFT JOIN candidate_committee cc "
            "    ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "  LEFT JOIN contributions ct "
            "    ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
            "  WHERE c.office = 'H' AND c.election_yr = :yr "
            "  GROUP BY c.office_state, c.district, c.cand_id, c.name, c.party) ")
    else:  # receipts (default) or individual: official FEC totals
        col = "individual_total" if metric == "individual" else "receipts"
        cand = (
            "cand AS (SELECT c.office_state, c.district, c.cand_id, c.name, c.party, "
            f"  COALESCE(MAX(t.{col}), 0) AS v FROM candidates c "
            "  LEFT JOIN candidate_totals t ON t.cand_id = c.cand_id AND t.cycle = :yr "
            "  WHERE c.office = 'H' AND c.election_yr = :yr "
            "  GROUP BY c.office_state, c.district, c.cand_id, c.name, c.party) ")
    # Exclude zero-total seats only when ranking ascending, so "least funded"
    # means genuinely low rather than absent-from-the-dataset.
    having = "WHERE d.total > 0 " if direction == "ASC" else ""
    sql = (
        "WITH " + cand +
        ", dist AS (SELECT office_state, district, SUM(v) AS total FROM cand "
        "  GROUP BY office_state, district) "
        ", leader AS (SELECT DISTINCT ON (office_state, district) "
        "    office_state, district, cand_id, name, party "
        "  FROM cand ORDER BY office_state, district, v DESC) "
        "SELECT d.office_state, d.district, l.cand_id, l.name, l.party, d.total "
        "FROM dist d JOIN leader l USING (office_state, district) "
        + having +
        f"ORDER BY d.total {direction}, d.office_state, d.district LIMIT :lim"
    )
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"yr": election_yr, "lim": limit}).all()
    return [RankedDistrict(state=r[0], district=r[1], cand_id=r[2], name=r[3],
                           party=r[4], value=Decimal(r[5])) for r in rows]


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


def industry_buckets() -> list[str]:
    # The industry names top_by_industry can rank on (from the classifier rules).
    return [name for name, _ in _INDUSTRY_RULES]


def _match_industry(industry: str) -> tuple[str, tuple[str, ...]] | None:
    q = (industry or "").strip().lower()
    if not q:
        return None
    for name, keywords in _INDUSTRY_RULES:
        if q == name.lower() or q in name.lower() or name.lower().startswith(q):
            return name, keywords
    return None


def top_candidates_by_industry(engine: Engine, industry: str, *, limit: int = 10,
                               election_yr: int = 2024) -> tuple[str | None, list[RankedCandidate]]:
    # Nationwide: the House candidates whose itemized donors' employers fall in a
    # given industry bucket give the most. Industry money is inherently itemized
    # (only itemized receipts carry an employer), so this reads itemized rows.
    match = _match_industry(industry)
    if match is None:
        return None, []
    name, keywords = match
    clauses = " OR ".join(
        f"UPPER(COALESCE(ct.employer, '')) LIKE :k{i}" for i in range(len(keywords)))
    params: dict = {f"k{i}": f"%{kw}%" for i, kw in enumerate(keywords)}
    params.update({"yr": election_yr, "lim": limit})
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT c.cand_id, c.name, c.office_state, c.district, c.party, "
            "  SUM(ct.amount) AS amt FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "JOIN candidates c ON c.cand_id = cc.cand_id "
            "  AND c.election_yr = cc.election_yr "
            "WHERE c.office = 'H' AND c.election_yr = :yr "
            "  AND COALESCE(ct.memo_cd, '') <> 'X' AND (" + clauses + ") "
            "GROUP BY c.cand_id, c.name, c.office_state, c.district, c.party "
            "ORDER BY amt DESC LIMIT :lim"
        ), params).all()
    return name, [RankedCandidate(cand_id=r[0], name=r[1], state=r[2], district=r[3],
                                  party=r[4], value=Decimal(r[5])) for r in rows]


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

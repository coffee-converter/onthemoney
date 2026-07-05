"""Fetch a small, bounded FEC slice via the public FEC API and write it in the
same pipe-delimited layout the bulk loader (`otm_data.ingest`) consumes.

This avoids downloading the multi-gigabyte bulk `itcont` file: it pulls only a
handful of districts through the API, so a demo dataset stays small. Get a free
key at https://api.data.gov/signup/ and pass it via `--api-key` or `FEC_API_KEY`.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.open.fec.gov/v1"

# A curated set of competitive 2024 U.S. House districts. Each also has a
# centroid in the front end's districts.json, so the map can fly to it.
DEFAULT_DISTRICTS = [("AZ", "06"), ("CA", "22"), ("PA", "08"), ("TX", "34")]


class FecApiClient:
    def __init__(self, api_key: str, base: str = API_BASE):
        self._key = api_key
        self._base = base

    def _get(self, path: str, params: dict) -> list[dict]:
        params = {**params, "api_key": self._key}
        url = f"{self._base}{path}?{urllib.parse.urlencode(params)}"
        last: Exception | None = None
        delay = 3
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    return json.loads(resp.read()).get("results", [])
            except urllib.error.HTTPError as err:
                if err.code == 429 and attempt < 3:  # rate limited: back off
                    time.sleep(delay)
                    delay *= 2
                    last = err
                    continue
                raise
            except TimeoutError as err:  # Schedule A can be slow
                last = err
        raise last  # type: ignore[misc]

    def candidates(self, state: str, district: str, cycle: int) -> list[dict]:
        return self._get("/candidates/", {
            "office": "H", "state": state, "district": district,
            "cycle": cycle, "per_page": 20,
        })

    def committees(self, candidate_id: str, cycle: int) -> list[dict]:
        return self._get(f"/candidate/{candidate_id}/committees/", {
            "cycle": cycle, "designation": "P",
        })

    def schedule_a(self, committee_id: str, cycle: int, limit: int) -> list[dict]:
        return self._get("/schedules/schedule_a/", {
            "committee_id": committee_id,
            "two_year_transaction_period": cycle,
            "is_individual": "true",
            "per_page": min(limit, 100),
        })


def _join(fields: list) -> str:
    # FEC API values can be null; render None as an empty field.
    return "|".join("" if x is None else str(x) for x in fields)


def _fec_date(iso: str) -> str:
    # "2024-06-15T00:00:00" or "2024-06-15" -> "06152024"
    if not iso or len(iso) < 10:
        return ""
    y, m, d = iso[0:4], iso[5:7], iso[8:10]
    return f"{m}{d}{y}"


def _amount(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def candidate_line(cand: dict, cycle: int, pcc_id: str) -> str:
    f = [""] * 10
    f[0] = cand.get("candidate_id", "")
    f[1] = cand.get("name", "")
    f[2] = cand.get("party", "")
    f[3] = str(cycle)
    f[4] = cand.get("state", "")
    f[5] = cand.get("office", "H")
    f[6] = str(cand.get("district", "")).zfill(2)
    f[9] = pcc_id
    return _join(f)


def committee_line(cmte: dict, candidate_id: str) -> str:
    f = [""] * 15
    f[0] = cmte.get("committee_id", "")
    f[1] = cmte.get("name", "")
    f[14] = candidate_id
    return _join(f)


def linkage_line(candidate_id: str, committee_id: str, cycle: int) -> str:
    f = [""] * 6
    f[0] = candidate_id
    f[2] = str(cycle)
    f[3] = committee_id
    return _join(f)


def contribution_line(contrib: dict, committee_id: str) -> str:
    f = [""] * 21
    f[0] = committee_id
    f[6] = "IND"
    f[7] = contrib.get("contributor_name", "")
    f[8] = contrib.get("contributor_city", "")
    f[9] = contrib.get("contributor_state", "")
    f[10] = contrib.get("contributor_zip", "")
    f[11] = contrib.get("contributor_employer", "")
    f[12] = contrib.get("contributor_occupation", "")
    f[13] = _fec_date(contrib.get("contribution_receipt_date", ""))
    f[14] = _amount(contrib.get("contribution_receipt_amount", 0))
    f[18] = contrib.get("memo_code") or ""
    f[20] = str(contrib.get("sub_id", ""))
    return _join(f)


def _safe(fn, label: str):
    # Skip a slow or unreachable endpoint instead of aborting the whole fetch;
    # a real auth/rate-limit error (HTTPError) still propagates.
    try:
        return fn()
    except urllib.error.HTTPError:
        raise
    except (TimeoutError, urllib.error.URLError, OSError) as err:
        print(f"  warn: {label} failed ({err}); skipping", file=sys.stderr)
        return []


def build_slice(client, districts, *, cycle: int = 2024,
                per_committee: int = 50) -> dict[str, list[str]]:
    cn: list[str] = []
    cm: list[str] = []
    ccl: list[str] = []
    itcont: list[str] = []
    for state, district in districts:
        for cand in _safe(lambda: client.candidates(state, district, cycle),
                          f"{state}-{district} candidates"):
            cand_id = cand.get("candidate_id", "")
            cmtes = _safe(lambda: client.committees(cand_id, cycle),
                          f"committees for {cand_id}")
            pcc = cmtes[0].get("committee_id", "") if cmtes else ""
            cn.append(candidate_line(cand, cycle, pcc))
            for cmte in cmtes:
                cid = cmte.get("committee_id", "")
                cm.append(committee_line(cmte, cand_id))
                ccl.append(linkage_line(cand_id, cid, cycle))
                for contrib in _safe(lambda: client.schedule_a(cid, cycle, per_committee),
                                     f"contributions for {cid}"):
                    itcont.append(contribution_line(contrib, cid))
    return {"cn": cn, "cm": cm, "ccl": ccl, "itcont": itcont}


def write_slice(lines: dict[str, list[str]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in lines.items():
        (out_dir / f"{name}.txt").write_text("\n".join(rows) + ("\n" if rows else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch a bounded FEC slice via the API.")
    ap.add_argument("--api-key", default=os.environ.get("FEC_API_KEY", "DEMO_KEY"))
    ap.add_argument("--out-dir", type=Path, default=Path("./_fec"))
    ap.add_argument("--cycle", type=int, default=2024)
    ap.add_argument("--per-committee", type=int, default=50)
    args = ap.parse_args()

    client = FecApiClient(args.api_key)
    try:
        lines = build_slice(client, DEFAULT_DISTRICTS, cycle=args.cycle,
                            per_committee=args.per_committee)
    except urllib.error.HTTPError as err:
        if err.code == 429:
            raise SystemExit(
                "FEC API rate limit hit (HTTP 429). The demo key is heavily "
                "throttled; get a free key at https://api.data.gov/signup/ and "
                "pass it as FEC_API_KEY, or wait a minute and retry."
            )
        raise SystemExit(f"FEC API error: HTTP {err.code} {err.reason}")
    except urllib.error.URLError as err:
        raise SystemExit(f"Could not reach the FEC API: {err.reason}")
    write_slice(lines, args.out_dir)
    for name, rows in lines.items():
        print(f"{name}: {len(rows)}")
    print(f"wrote to {args.out_dir}; now run: "
          f"python -m otm_data.ingest --cycle {args.cycle} --data-dir {args.out_dir}")


if __name__ == "__main__":
    main()

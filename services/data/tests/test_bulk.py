import zipfile
from sqlalchemy import text
from otm_data.bulk import bulk_load_contributions, weball_total_line
from otm_data.load import (
    load_candidates, load_committees, load_linkages, linked_committee_ids,
)


def test_bulk_load_contributions_copies_linked_ind_only(db_engine, tmp_path):
    load_candidates(db_engine, [
        "H2AZ06099|CISCOMANI, JUAN|REP|2024|AZ|H|06|I|C|C00770886|123 MAIN ST||TUCSON|AZ|85701",
    ])
    load_committees(db_engine, [
        "C00770886|CISCOMANI FOR CONGRESS|SMITH, JANE|PO BOX 1||TUCSON|AZ|85701|P|H|REP|Q|||H2AZ06099",
    ])
    load_linkages(db_engine, ["H2AZ06099|2024|2024|C00770886|H|P|LNK123"])
    cmte_ids = linked_committee_ids(db_engine)

    z = tmp_path / "indiv24.zip"
    lines = [
        # linked committee, IND -> kept
        "C00770886|N|Q2|P|202400000|15|IND|DOE, JOHN|TUCSON|AZ|85701|ACME|ENG|06152024|500.00||T1|1|||SUBA",
        # unlinked committee -> dropped
        "C00999999|N|Q2|P|202400001|15|IND|ROE, JANE|MESA|AZ|85201|SELF|X|06162024|100.00||T2|1|||SUBB",
        # non-individual -> dropped
        "C00770886|N|Q2|P|202400002|15|ORG|ACME PAC|TUCSON|AZ|85701|||06172024|999.00||T3|1|||SUBC",
    ]
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("itcont.txt", "\n".join(lines) + "\n")

    n = bulk_load_contributions(db_engine, z, cmte_ids=cmte_ids)
    assert n == 1
    with db_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM contributions")).scalar() == 1
        row = conn.execute(text("SELECT name, amount FROM contributions")).first()
    assert row[0] == "DOE, JOHN"
    assert str(row[1]) == "500.00"


def _mkzip(path, member, lines):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, "\n".join(lines) + "\n")


def test_run_bulk_ingest_house_slice_only(db_engine, tmp_path):
    from otm_data.bulk_ingest import run_bulk_ingest

    _mkzip(tmp_path / "cn24.zip", "cn.txt", [
        "H2AZ06099|CISCOMANI, JUAN|REP|2024|AZ|H|06|I|C|C00770886|123 MAIN ST||TUCSON|AZ|85701",
        "S4AZ00099|SENATOR, SAM|DEM|2024|AZ|S|00|C|C|C00999999|||PHOENIX|AZ|85001",
    ])
    _mkzip(tmp_path / "cm24.zip", "cm.txt", [
        "C00770886|CISCOMANI FOR CONGRESS|SMITH, JANE|PO BOX 1||TUCSON|AZ|85701|P|H|REP|Q|||H2AZ06099",
        "C00999999|SENATE CMTE|X|ADDR||PHX|AZ|85001|P|S|DEM|Q|||S4AZ00099",
    ])
    _mkzip(tmp_path / "ccl24.zip", "ccl.txt", [
        "H2AZ06099|2024|2024|C00770886|H|P|LNK1",
        "S4AZ00099|2024|2024|C00999999|S|P|LNK2",
    ])
    _mkzip(tmp_path / "weball24.zip", "weball.txt", [
        "|".join(["H2AZ06099", "CISCOMANI", "I", "REP", "REP", "1000.00"]
                 + ["0"] * 11 + ["800.00", "AZ", "06"]),
    ])
    _mkzip(tmp_path / "indiv24.zip", "itcont.txt", [
        "C00770886|N|Q2|P|1|15|IND|DOE, JOHN|TUCSON|AZ|85701|ACME|ENG|06152024|500.00||T1|1|||SUBA",
        "C00999999|N|Q2|P|2|15|IND|SEN, DONOR|PHOENIX|AZ|85001|X|Y|06162024|700.00||T2|1|||SUBB",
    ])

    counts = run_bulk_ingest(db_engine, data_dir=tmp_path, cycle=2024)
    assert counts["candidates"] == 1        # House only (Senate dropped)
    assert counts["house_committees"] == 1
    assert counts["contributions"] == 1     # only the House committee's IND row
    assert counts["totals"] == 1


def test_weball_total_line():
    fields = ["H0IL05096", "QUIGLEY, MIKE", "I", "DEM", "DEM", "1093681.39",
              "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "363190.52",
              "IL", "05"]
    assert weball_total_line("|".join(fields), 2024) == \
        "H0IL05096|2024|1093681.39|363190.52"

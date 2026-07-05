from pathlib import Path
from sqlalchemy import text
from otm_data.ingest import run_ingest


def test_run_ingest_loads_slice(db_engine, tmp_path):
    # stage the fixture files under the names the CLI expects
    for src, dst in [("cn_sample.txt", "cn.txt"), ("cm_sample.txt", "cm.txt"),
                     ("ccl_sample.txt", "ccl.txt"), ("itcont_sample.txt", "itcont.txt")]:
        (tmp_path / dst).write_text(Path(f"tests/fixtures/{src}").read_text())

    counts = run_ingest(db_engine, data_dir=tmp_path, cycle=2024)
    assert counts == {"candidates": 1, "committees": 1, "linkages": 1,
                      "contributions": 2, "totals": 0}
    with db_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM contributions")).scalar() == 2

from otm_eval.coverage import coverage_stats


def test_coverage_stats_counts_house(seeded_engine):
    stats = coverage_stats(seeded_engine)
    assert stats["cycle"] == 2024
    assert stats["districts"] == 1        # AZ-06
    assert stats["candidates"] == 1
    assert stats["contributions"] == 2    # both IND rows load; memo filtered at query time

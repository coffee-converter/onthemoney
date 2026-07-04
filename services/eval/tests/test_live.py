import os
import pytest
from otm_eval.golden import load_golden
from otm_eval.live import system_output_from_live


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"),
                    reason="needs ANTHROPIC_API_KEY for the model path")
def test_live_system_output_for_az06(seeded_engine):
    from anthropic import Anthropic
    item = next(i for i in load_golden() if i.id == "az06-funds")
    out = system_output_from_live(seeded_engine, item, Anthropic())
    assert "resolve_entity" in out.tools_called
    assert out.total == "500.00"
    assert out.committees == ["C00770886"]

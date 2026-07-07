regression-demo:
	cd services/eval && uv run python -m otm_eval.regression_demo
	cp services/eval/otm_eval/data/regression.json apps/web/lib/regression.json

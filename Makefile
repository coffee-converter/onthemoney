.PHONY: regenerate regression-demo

# Regenerate every derived eval artifact in dependency order after the
# underlying DB/baseline changes: the golden set + recorded baseline first,
# then the regression-demo artifact (which the /how-it-works page imports).
# Use this rather than running otm_eval.regenerate on its own, or the web's
# regression.json copy will drift out of sync with the fresh baseline.
regenerate:
	cd services/eval && uv run python -m otm_eval.regenerate
	$(MAKE) regression-demo

regression-demo:
	cd services/eval && uv run python -m otm_eval.regression_demo
	cp services/eval/otm_eval/data/regression.json apps/web/lib/regression.json

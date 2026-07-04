# On The Money

**A conversational accountability atlas.** Ask how money and power actually flow; an agent resolves your question against real public data, steers a live map into the answer, and reports it - cited, confidence-scored, and provably correct.

`onthemoney.fyi`

## Why it's different

Most AI products can't tell you whether their answers are trustworthy. On The Money is built in a domain with **objective, computable ground truth** - campaign-finance filings are a matter of record, not opinion. That lets the agent be graded against **facts, not vibes**: a golden-dataset eval harness with deterministic assertions, CI regression gates, and a public accuracy/calibration scoreboard.

- **Cited** - every figure links to its source filing.
- **Calibrated** - honest confidence, and an explicit "insufficient evidence" state.
- **Provable** - a public scoreboard shows how accurate the agent is, over time.

## Status

Early build. v1 slice: 2024 cycle · U.S. House · individual itemized receipts (FEC bulk data).

## Architecture

- `services/data` - deterministic FEC ground-truth oracle (Postgres). No LLM.
- _(coming)_ `services/agent` - Python agent + tools.
- _(coming)_ `apps/api` - NestJS API boundary.
- _(coming)_ `apps/web` - Next.js + MapLibre front end.

Build plans live in `docs/superpowers/plans/`.

## Non-partisan by design

On The Money makes the public record legible. All output is strictly descriptive - no endorsements, no editorializing, no predictions.

## License

MIT

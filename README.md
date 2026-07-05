# On The Money

A conversational accountability atlas. Ask how money and power flow, and an agent resolves the question against real public data, moves a live map to the answer, and reports it with citations and a confidence score.

`onthemoney.fyi`

[![CI](https://github.com/coffee-converter/onthemoney/actions/workflows/ci.yml/badge.svg)](https://github.com/coffee-converter/onthemoney/actions/workflows/ci.yml)

## Why it's different

Most products in this space can't tell you whether their answers are trustworthy. On The Money works in a domain with objective, computable ground truth: campaign-finance filings are a matter of record. That lets the agent be graded against facts rather than opinion, using a golden-dataset eval harness with deterministic assertions, CI regression gates, and a public accuracy scoreboard.

- **Cited.** Every figure links to its source filing.
- **Calibrated.** Honest confidence, with an explicit "insufficient evidence" state.
- **Provable.** A public scoreboard shows accuracy over time.

## Status

Early build. The v1 slice covers the 2024 cycle, U.S. House races, and individual itemized receipts from FEC bulk data.

## Architecture

- `services/data`: deterministic FEC ground-truth store (Postgres). No inference.
- `services/agent`: Python agent. A shared tool registry drives a standalone MCP server, a pure-Python Anthropic tool-use runtime, a LangGraph verify-and-calibrate step, and a FastAPI service with streaming.
- `services/eval`: golden dataset, deterministic graders, a CI gate that fails on regression, and the scoreboard.
- `apps/api`: NestJS backend-for-frontend. Typed contracts, stream relay, scoreboard endpoint.
- `apps/web`: Next.js and MapLibre. The steerable atlas, the streamed step trace, calibrated confidence, and citations.

## Non-partisan by design

On The Money makes the public record legible. All output is descriptive: no endorsements, no editorializing, no predictions.

## License

MIT

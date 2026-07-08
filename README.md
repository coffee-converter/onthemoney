# On The Money

### ▶ Live demo: **[onthemoney.fyi](https://onthemoney.fyi)**

A conversational accountability atlas for U.S. House campaign finance. Ask a question in plain English, and an agent resolves it against real FEC filings, analyzes the money, draws the answer on a live map, and reports it with citations and a calibrated confidence score.

[![CI](https://github.com/coffee-converter/onthemoney/actions/workflows/ci.yml/badge.svg)](https://github.com/coffee-converter/onthemoney/actions/workflows/ci.yml)

[![On The Money: a plain-English question streams into a live money-flow map, with candidate switching and a confidence-scored, cited answer](assets/hero.gif)](https://onthemoney.fyi)

> **Recruiter / reviewer note:** the fastest way to see this is the live demo above.
> Ask *"Who funds the representative in NY-14?"* and watch the agent work.

## Why it's different

Most conversational data products can't tell you whether their answers are trustworthy. On The Money works in a domain with objective, computable ground truth: campaign-finance filings are a matter of record. That lets the agent be graded against facts rather than opinion.

- **Grounded.** The numbers an answer reports (totals, industry and geographic breakdowns, rankings) come from tool calls against the FEC data, not the model's memory, and are returned as structured fields alongside the prose so they can be checked. The visualizations are grounded the same way: the agent names what to draw in semantic terms (district ids, values, colors) and the backend resolves them to real coordinates, so a map is provably correct or it does not render.
- **Cited.** Where an answer resolves a specific candidate, it links back to that candidate's FEC committee filings.
- **Calibrated.** Each answer commits to a confidence state (high, partial, or an explicit "insufficient evidence" instead of a confident guess), and that calibration is graded against ground truth by the eval harness (a Brier score on the public scoreboard), not merely asserted.
- **Verifiable.** A golden-dataset eval harness with deterministic graders runs in CI and backs the public accuracy scoreboard.

## What you can ask

The agent plans each question, calls the tools it needs, and picks a visualization that fits.

- **Locate** a district: *Where is Illinois district 4?*
- **Follow the money** into a seat: *Who funds the representative in NY-14?* (draws the donor-state money-flow map)
- **Look someone up by name:** *Where does Marjorie Taylor Greene's money come from?* (grounds the name to a real district, then answers)
- **Break down the funding:** *What industries fund NY-14?* / *Is this candidate grassroots-funded?* / *How much of their money is out of state?*
- **Rank nationwide:** *Who are the 10 best-funded House candidates in the country?*
- **Map at any scale:** a single district, a whole state colored by party or shaded by dollars, the entire country as a state-level heat map, or a nationwide scatter of the top raisers.
- **Compare and normalize:** *Which states raise the most per district?* / *Is AOC or Marjorie Taylor Greene more grassroots-funded?*
- **Size up a race:** *How competitive is the race in TX-15?*

Every answer stays strictly descriptive. No endorsements, no predictions, no editorializing.

## How it works

A single question can fan out into several tool calls: resolve the entity, pull the funding totals, break the money down by industry or donor geography, and choose a map. The agent composes these itself and streams its steps to the UI as it goes.

The map is a small visualization vocabulary the agent draws from:

- `highlight_district` to locate a seat
- `emit_scene` for the donor-state money-flow view
- `map_state` and `map_nation` for state and national choropleths (heat or party color, labeled)
- `map_candidates` for a nationwide scatter of ranked candidates
- `render_map` for anything bespoke

Aggregate maps are built server-side from the data, so a request for "every district in Texas" is assembled from ground truth rather than transcribed by the model. That keeps large visualizations both reliable and verifiable.

## Data

The v1 slice covers the 2024 cycle, all U.S. House races, and individual itemized receipts from FEC bulk data: nearly four million contributions across every House district, loaded into Postgres as a deterministic ground-truth store with no inference in the data layer.

Itemized individual contributions carry donor geography and employer detail. Small unitemized donations are reported only in aggregate, and the agent is explicit about that boundary when it matters.

## Architecture

- `services/data`: deterministic FEC ground-truth store (Postgres). Bulk ingest, typed queries, no inference.
- `services/agent`: Python agent. A shared tool registry drives a standalone MCP server, a pure-Python Anthropic tool-use runtime, a LangGraph verify-and-calibrate step, and a FastAPI service with streaming.
- `services/eval`: golden dataset, deterministic graders, a CI gate that fails on regression, and the accuracy scoreboard (a snapshot regenerated with `make regenerate`).
- `apps/api`: NestJS backend-for-frontend. Typed contracts, server-sent-event stream relay, scoreboard endpoint.
- `apps/web`: Next.js and MapLibre. The steerable atlas, the streamed step trace, calibrated confidence, and citations.

The tool registry is the spine: one definition of each tool feeds the runtime, the MCP server, and the eval harness, so the agent's capabilities, its public interface, and its tests do not drift apart.

## Run it locally

You need an `ANTHROPIC_API_KEY`. Postgres 16 and Node are the only other prerequisites.

```bash
ANTHROPIC_API_KEY=sk-ant-... ./scripts/dev.sh   # Postgres, data, agent, BFF
cd apps/web && npm run dev                        # then open http://localhost:3000
```

`scripts/dev.sh` boots Postgres, loads FEC data (set `FEC_API_KEY` for the full pull, or it falls back to a small demo slice), and starts the agent and BFF. The API key lives only on the agent service and never reaches the browser.

## Non-partisan by design

On The Money makes the public record legible. All output is descriptive: no endorsements, no editorializing, no predictions.

## License

MIT

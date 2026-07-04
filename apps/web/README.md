# otm-web

The Next.js front end: a MapLibre atlas the agent steers, a conversational rail that streams the agent's steps, and a public eval scoreboard.

## What it does

- Ask a question in the rail. The BFF streams each agent step (tool calls, results) as it happens.
- When the agent emits a scene, the map flies to the district and paints the money flows.
- The answer shows a confidence chip and source citations.
- The Scoreboard page renders the eval accuracy and calibration.

## Config

- `NEXT_PUBLIC_API_URL`: BFF base URL (default `http://localhost:3001`).
- `NEXT_PUBLIC_MAP_STYLE`: MapLibre style URL (default the public demo tiles).

## Develop

```bash
npm install
npm test        # vitest: scene mapping, components, api client
npm run typecheck
npm run dev
```

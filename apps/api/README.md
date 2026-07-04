# otm-api

The backend-for-frontend. It owns the typed contracts the web app depends on, proxies questions to the agent service, relays the streamed step trace as server-sent events, and serves the eval scoreboard.

## Endpoints

- `POST /ask` with `{ "query": "..." }`: proxies to the agent service and returns `{ trace, answer }`.
- `GET /ask/stream?query=...`: server-sent events relaying each agent step, then a final `answer` event.
- `GET /scoreboard`: the latest eval scoreboard (accuracy, calibration, per-item results).

## Config

- `AGENT_URL`: base URL of the agent service (default `http://localhost:8000`).
- `SCOREBOARD_PATH`: path to the scoreboard JSON (default bundled artifact).
- `PORT`: listen port (default `3001`).

## Develop

```bash
npm install
npm test        # jest, no running services needed
npm run build
npm start
```

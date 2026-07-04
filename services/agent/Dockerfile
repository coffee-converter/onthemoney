# Build from the repository root so the otm-data path dependency is available:
#   docker build -f services/agent/Dockerfile -t otm-agent .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY services/data /app/services/data
COPY services/agent /app/services/agent

WORKDIR /app/services/agent
RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "otm_agent.http"]

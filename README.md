# Sevo

**Sevo tells you what matters across your apps without making you open the feed.**

This repository currently implements **Phase 1**: a deterministic fake-data pipeline. Hermes and LM Studio are intentionally not connected yet.

## Tech Stack

- Python, FastAPI, Pydantic
- SQLite
- HTML, CSS, JavaScript, nginx
- Docker Compose
- pytest
- LM Studio and Hermes Agent (planned for Phase 2)

## What works

- FastAPI backend and SQLite event store
- Read-only fake X, Eufy metadata, and Calendar adapters
- Deterministic natural-language questions and cross-source catch-up ranking
- Responsive, feed-free web interface with an Ask Sevo field
- Partial briefings when one source fails
- Docker isolation with no broad host mounts or Docker socket access

## Start with Docker

Requirements: Docker Desktop. LM Studio is not needed until Phase 2.

```bash
git clone <repository-url>
cd sevo
cp .env.example .env   # optional; defaults work without this file
docker compose up --build
```

Open <http://localhost:3000>, then select **Catch me up**.

To use Sevo from iPhone Safari on the same trusted network, find the Mac's LAN address and open `http://<mac-lan-ip>:3000`. Phase 1 has no authentication, so do not expose this port to the public internet.

Stop Sevo with:

```bash
docker compose down
```

The SQLite database is retained in the Docker volume `sevo_storage`. Remove it only when you intentionally want to reset local events:

```bash
docker compose down -v
```

## API

The frontend proxies API calls to the backend:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service health |
| `GET` | `/api/sources` | Configured fake sources |
| `GET` | `/api/events?limit=50` | Recent normalized events |
| `POST` | `/api/chat` | Ask about fake camera, X, or Calendar data |
| `POST` | `/api/catch-up` | Concise deterministic briefing |

Example:

```bash
curl -X POST http://localhost:3000/api/catch-up
curl -X POST http://localhost:3000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Was there movement at the front door?"}'
```

Phase 1 question routing is deliberately deterministic. It supports camera activity, X trends, upcoming Calendar events, and catch-up requests without interpreting arbitrary instructions or accessing unapproved tools.

## Run tests locally

Python 3.12 is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
pytest backend/tests
```

Tests use temporary SQLite databases and fake data only. No credentials or external services are required.

## Project layout

```text
backend/       FastAPI app, tools, event store, and tests
frontend/      Static responsive UI served by nginx
data/          Project-owned fake source records
docker-compose.yml
```

## Configuration

See `.env.example`. The Phase 2 LM Studio variables are included for forward compatibility but are not consumed by the Phase 1 pipeline. LM Studio will remain on the macOS host and will eventually be reached at `host.docker.internal`.

The backend container runs as a non-root user. It receives only:

- `./data` mounted read-only
- a Sevo-owned SQLite volume mounted at `/app/storage`

It does not receive the Docker socket, home directory, browser data, credentials, or arbitrary host filesystem access.

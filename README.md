# VirusTotal Data Pipeline

A two-service data pipeline that fetches threat intelligence from the VirusTotal API, persists it in PostgreSQL, caches it in Redis, and exposes it via a FastAPI REST API.

---

## Architecture

```
┌─────────────────────────────┐        ┌─────────────────────────────┐
│     Background Service      │        │         API Service          │
│                             │        │                              │
│  Seed List (IPs/Domains/    │        │  Incoming Request            │
│  Hashes)                    │        │         │                    │
│         │                   │        │         ▼                    │
│         ▼                   │        │   Redis Cache ── HIT ──────► │ Return (source: cache)
│   Rate Limiter              │        │         │                    │
│   (4 req/min)               │        │        MISS                  │
│         │                   │        │         │                    │
│         ▼                   │        │         ▼                    │
│   VirusTotal API            │        │    PostgreSQL ── HIT ──────► │ Repopulate Cache
│         │                   │        │         │                    │   ▼
│         ▼                   │        │        MISS                  │ Return (source: db)
│   Parse & Store ───────────────────► │         │                    │
│         │          shared   │        │         ▼                    │
│         ▼                   │        │   VirusTotal API (fallback)  │
│   PostgreSQL  ◄─── shared ──────────►│   Parse & Store              │
│   Redis       ◄─── shared ──────────►│         │                    │
│  (pre-warm cache)           │        │         ▼                    │
└─────────────────────────────┘        │   Return (source: virustotal)│
                                       └─────────────────────────────┘
```

**Background service** periodically ingests a finite seed list into PostgreSQL and pre-warms Redis.  
**API service** reads from Redis → PostgreSQL → falls back to VT for missing data points.  
**Shared infrastructure:** PostgreSQL (source of truth) + Redis (performance layer, 5 min TTL).

---

## Services

### Background Service
- Reads from a static seed list of IPs, domains, and file hashes
- Fetches reports from VirusTotal respecting the 4 req/min rate limit (1 request every 15 seconds)
- Stores results in PostgreSQL and pre-warms Redis cache
- Runs as a standalone process independent of the API service

### API Service
- Serves data via REST API
- Lookup order: Redis → PostgreSQL → VirusTotal (fallback for missing data points)
- Does not depend on or communicate with the background service directly

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/ip/{ip}` | Fetch report for an IP address |
| `GET` | `/api/v1/domain/{domain}` | Fetch report for a domain |
| `GET` | `/api/v1/filehash/{hash}` | Fetch report for a SHA-256 file hash |

### Query Params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `refresh` | `bool` | `false` | Force re-fetch from VT, bypass cache and DB |

### Example Requests

```bash
# IP lookup
GET /api/v1/ip/142.250.0.0

# Domain lookup
GET /api/v1/domain/google.com

# File hash lookup
GET /api/v1/filehash/275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f

# Force refresh
GET /api/v1/domain/google.com?refresh=true
```

## Test Identifiers

| Type | Value |
|------|-------|
| IP | `142.250.0.0` (Google) |
| Domain | `google.com` |
| File Hash (SHA-256) | `275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f` (EICAR test virus) |

---

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- VirusTotal API key ([get one free here](https://www.virustotal.com/gui/my-apikey))

### Environment Variables

Create a `.env` file in the project root:

```env
DB_NAME=
DB_USERNAME=
DB_PASSWORD=
DB_HOST=
DB_PORT=
REDIS_HOST=
REDIS_PORT=
VT_API_KEY=
```

### Run

```bash
# 1. Clone the repo and cd into it
git clone <repo-url> && cd virus-total-data-pipeline

# 2. Update DB credentials in init.sql if needed
#    Script defaults: role=vt_user | password=vt_password
#    File: /app/database/init.sql

# 3. Install dependencies and set up virtual environment
make setup

# 4. Create database and tables
make database

# 5. Start the background service (fetches seed list into DB + cache)
make fetcher

# 6. Start the API service (in a separate terminal)
make app-service
```

API available at: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## Project Structure

```
virus-total-data-pipeline/
├── app/                      # API Service
│   ├── database
│   │   ├── __init__.py
│   │   └── init.sql          # DB schema + setup
│   ├── __init__.py
│   ├── main.py
│   └── router
│       ├── app_router.py     # API endpoints
│       └── __init__.py
├── architecture.md
├── background-service        # Background Service
│   ├── database.py
│   ├── data.json
│   ├── __init__.py
│   ├── main.py
│   └── service.py
├── Makefile
├── README.md
└── requirements.txt
```

---

## Design Decisions

- **Two independent services** — background service and API service share only PostgreSQL and Redis. They do not communicate directly.
- **Shared Redis as pre-warm layer** — background service writes to Postgersql DB on ingest. API service benefits from cache hits on matching queries. Redis is a performance layer; PostgreSQL is the source of truth.
- **5 min TTL** — short enough to stay reasonably fresh, long enough to absorb repeated queries between background service runs.
- **Fallback fetch on missing data** — if a queried identifier was not in the background service seed list, the API service falls back to fetching from VT directly, stores it, and returns it. This keeps the API useful beyond the finite seed list.
- **`refresh` query param** — instead of a separate endpoint, `?refresh=true` on any GET forces a re-fetch from VT and updates both DB and cache.
- **`source` field in response** — shows whether data came from `cache`, `db`, or `virustotal`. Useful for debugging and demonstrating pipeline behaviour.
- **Server-side rate limiting** — Redis counter enforces 4 req/min before hitting VT in both services, preventing upstream 429s.
- **Static seed list** — background service reads from a `data.json` file. Easily extendable to pull from external threat intel feeds.
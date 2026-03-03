# VirusTotal Data Pipeline

A data pipeline that fetches data from the VirusTotal API, persists it in PostgreSQL, and caches it in Redis — exposed via a FastAPI REST API.

---

## Architecture

```
Incoming Request
       │
       V
 Redis Cache ──── HIT ───> Return (source: cache)
       │
      MISS
       │
       V
  PostgreSQL ──── HIT ───> Repopulate Cache ───> Return (source: db)
       │
      MISS
       │
       V
 VirusTotal API
       │
       V
 Parse & Store ──> Write to DB + Cache ──> Return (source: virustotal)
```

**Cache strategy:** Write-through with 5m TTL.  
**Rate limiting:** Self-enforced at 4 requests/min via Redis counter (respects VT free tier limits).

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
- PostgreSQL (with proper db user)
- Redis
- VirusTotal API key ([get one free here](https://www.virustotal.com/gui/my-apikey))

### Environment Variables

Create a `.env` file in the project root:

```env
DB_NAME = "your-db-name"
DB_USERNAME = "your-db-username"
DB_PASSWORD = "your-db-password"
DB_HOST = "your-db-host"
DB_PORT = "your-db-port"
VT_API_KEY = "your-vt-api-key"
```

### Run

```bash
# 1. Clone the repo and cd into it
git clone <repo-url> && cd virus-total-data-pipeline

# 2. Change the db init.sql file accordingly to your postgresql setup
- /app/database/init.sql

# 3. Install dependencies and set up environment
make setup

# 4. Create database and tables
make database

# 5. Start the server
make run
```

API available at: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`


---

## Design Decisions

### - **Write-through cache** — every VT fetch writes to DB and Redis simultaneously, keeping both in sync.
### - **`refresh` query param** — instead of a separate endpoint, a single GET with `?refresh=true` keeps the API surface minimal and intuitive.
### - **`source` field in response** — transparency on where data came from; useful for debugging cache behaviour.
### - **Server-side rate limiting** — Redis counter enforces 4 req/min before hitting VT, avoiding 429s from the upstream API.
### - **No background cron** — ingest is lazy/on-demand. The `refresh` param handles manual re-ingest when fresh data is needed.
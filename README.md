# LRS Dashboard

A self-hosted **Learning Analytics** stack combining:

- **[Ralph LRS](https://openfun.github.io/ralph/latest/)** — xAPI-compliant Learning Record Store (High-performance ingestion)
- **[Redash](https://redash.io/)** — Data visualization & dashboarding (Frontend UI)
- **Elasticsearch** — Shared data backend

## Architecture

Ralph is a "headless" backend. It does not have a user interface. All dashboarding and visualization are handled by Redash, which connects directly to the Elasticsearch database where Ralph stores the incoming data.

```
┌─────────────┐      xAPI/HTTP       ┌──────────────┐
│  seed.py /  │ ──────────────────▶  │   Ralph LRS  │ :8100
│  LMS / App  │                      └──────┬───────┘
└─────────────┘                             │ stores
                                            ▼
                                    ┌───────────────┐
                                    │ Elasticsearch  │ :9200
                                    └───────┬───────┘
                                            │ queries
                                            ▼
                                    ┌───────────────┐
                                    │    Redash      │ :5005
                                    └───────────────┘
```

## Quick Start

### 1. Automated Setup
This script will pull the images, set up the containers, wait for Elasticsearch, provision the required index, and create the `.env` file.

```bash
cd LRS-Dashboard
chmod +x setup.sh
./setup.sh
```

### 2. Seeding Test Data
We have provided a robust mock data generator (`seed.py`) that simulates 30 users taking the "Cybersecurity: Phishing Defense & Data Protection" course with varying outcomes.

```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. ACTIVATE the environment (Required for 'pip' to work)
source venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Run the seeding script
python seed.py --target ralph   # Send data to Ralph/Elasticsearch
python seed.py --target sqllrs  # Send data to SQL LRS/PostgreSQL
```
*Note: If 'pip' still shows not found after activation, you can use `python -m pip install -r requirements.txt` instead.*
*Note: The seeding script uses `127.0.0.1` instead of `localhost` to bypass IPv6 connection reset issues common on Docker Desktop for Mac.*

### 3. Connect Redash to your Data Sources
Once the setup is complete and data is seeded, you must connect Redash to your LRS backends to view the data.

1. Open Redash at http://localhost:5005
2. Create your admin account if prompted.
3. Go to **Settings > Data Sources > New Data Source**.

**Option A: Connect to Ralph (Elasticsearch)**
- Select **Elasticsearch**.
- **Name:** Ralph LRS
- **Base URL:** `http://elasticsearch:9200`

**Option B: Connect to SQL LRS (PostgreSQL)**
- Select **PostgreSQL**.
- **Name:** SQL LRS
- **Host:** `postgres-lrs`
- **Port:** `5432`
- **User:** `lrsql`
- **Password:** `lrsql_secret`
- **Database Name:** `lrsql`

Click **Save** and **Test Connection** for whichever sources you added. You can now navigate to **Queries** and start querying your data!

## Services Overview

| Service | URL | Description |
|---------|-----|-------------|
| Redash | http://localhost:5005 | Dashboard & data visualization (Your UI) |
| Ralph LRS | http://localhost:8100 | xAPI Learning Record Store (Headless API) |
| Elasticsearch | http://localhost:9200 | Data storage backend for Ralph |
| SQL LRS | http://localhost:8080 | Alternative xAPI LRS using PostgreSQL |
| PostgreSQL | localhost:5432 | Data storage backend for SQL LRS |
| Redash (nginx) | http://localhost:80 | Production reverse proxy |

## Default Credentials

### Ralph LRS
- **Username:** `ralph`
- **Password:** `secret`

*(Used when sending POST requests to `/xAPI/statements`)*

### Redash
- Configured by you during the initial web setup at http://localhost:5005.

## Testing & Verifying Connections

### Verify Ralph LRS is running
*Note: In a single-node Elasticsearch setup, the cluster health is `yellow`. Ralph's strict heartbeat expects `green`, so this endpoint may return a 500 error locally, even though ingestion works perfectly.*
```bash
curl http://localhost:8100/__heartbeat__
```

### Verify Elasticsearch has the Seed Data
```bash
curl -s "http://localhost:9200/statements/_count"
# Expected: {"count":614, ...}
```

## Useful Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f ralph-lrs
docker compose logs -f redash-server

# Remove all data and start fresh (Destructive)
docker compose down -v
```

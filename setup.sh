#!/usr/bin/env bash
# =============================================================================
# LRS Dashboard — First-time Setup Script
# =============================================================================
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          LRS Dashboard — First-Time Setup                    ║"
echo "║          Redash  +  Ralph LRS  +  Elasticsearch              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ---- Step 1: Create .env from example if it doesn't exist -------------------
if [ ! -f .env ]; then
  echo "→ Creating .env from .env.example ..."
  cp .env.example .env

  # Generate random secrets
  COOKIE_SECRET=$(openssl rand -base64 32)
  SECRET_KEY=$(openssl rand -base64 32)
  PG_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')

  # Replace placeholder values (works on both macOS and Linux)
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|CHANGE_ME_cookie_secret_here|${COOKIE_SECRET}|" .env
    sed -i '' "s|CHANGE_ME_secret_key_here|${SECRET_KEY}|" .env
    sed -i '' "s|redash_secret|${PG_PASSWORD}|g" .env
  else
    sed -i "s|CHANGE_ME_cookie_secret_here|${COOKIE_SECRET}|" .env
    sed -i "s|CHANGE_ME_secret_key_here|${SECRET_KEY}|" .env
    sed -i "s|redash_secret|${PG_PASSWORD}|g" .env
  fi

  echo "  ✓ .env created with auto-generated secrets"
else
  echo "  ✓ .env already exists, skipping"
fi

# ---- Step 2: Pull images ----------------------------------------------------
echo ""
echo "→ Pulling Docker images (this may take a while on first run) ..."
docker compose pull

# ---- Step 3: Start infrastructure first -------------------------------------
echo ""
echo "→ Starting infrastructure services (Elasticsearch, PostgreSQL, Redis) ..."
docker compose up -d elasticsearch postgres redis

echo "→ Waiting for Elasticsearch to be healthy ..."
until docker compose exec -T elasticsearch curl -s http://localhost:9200/_cluster/health?wait_for_status=yellow > /dev/null 2>&1; do
  printf "."
  sleep 3
done
echo " ✓ Elasticsearch is ready"

echo "🔄 Waiting for Elasticsearch to be ready locally..."
until curl -s http://localhost:9200 >/dev/null; do
    echo "⏳ Elasticsearch is unavailable - sleeping..."
    sleep 2
done

echo "🛠️ Creating 'statements' index in Elasticsearch (if not exists)..."
curl -s -X PUT http://localhost:9200/statements > /dev/null 2>&1 || true

echo "🔄 Waiting for Redash to be ready..."
until docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
  printf "."
  sleep 2
done
echo " ✓ PostgreSQL is ready"

# ---- Step 4: Generate Ralph auth.json from .env credentials -----------------
echo ""
echo "→ Setting up Ralph LRS authentication ..."

# Read credentials from .env
source .env
RALPH_USER="${RALPH_AUTH_USER:-ralph}"
RALPH_PASS="${RALPH_AUTH_PASSWORD:-secret}"

docker compose up -d ralph
sleep 5

# Use a temporary python container to generate the bcrypt hash
echo "  → Generating secure password hash..."
HASH=$(docker run --rm python:3.9-slim bash -c "pip install -q bcrypt && python -c \"import bcrypt; print(bcrypt.hashpw('${RALPH_PASS}'.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8'))\"")

# Write the auth.json locally and copy it into the container
cat <<EOF > auth.json
[
  {
    "username": "${RALPH_USER}",
    "hash": "${HASH}",
    "scopes": ["statements/write", "statements/read/mine", "statements/read"],
    "agent": {"mbox": "mailto:${RALPH_USER}@example.com"}
  }
]
EOF

docker compose cp auth.json ralph:/app/.ralph/auth.json
rm auth.json
echo "  ✓ Ralph auth.json generated and copied (user: ${RALPH_USER} / password: ${RALPH_PASS})"

# ---- Step 5: Initialise Redash database & create admin ----------------------
echo ""
echo "→ Initialising Redash database ..."
docker compose run --rm redash-server create_db

REDASH_ADMIN_NAME="${REDASH_ADMIN_NAME:-Admin}"
REDASH_ADMIN_EMAIL="${REDASH_ADMIN_EMAIL:-admin@example.com}"
REDASH_ADMIN_PASSWORD="${REDASH_ADMIN_PASSWORD:-admin123}"

echo "→ Creating Redash admin user ..."
docker compose run --rm redash-server manage users create_root \
  "${REDASH_ADMIN_EMAIL}" "${REDASH_ADMIN_NAME}" \
  --password "${REDASH_ADMIN_PASSWORD}" || \
docker compose run --rm redash-server manage users create \
  --admin --password "${REDASH_ADMIN_PASSWORD}" \
  "${REDASH_ADMIN_EMAIL}" "${REDASH_ADMIN_NAME}" || \
echo "  ⚠ Could not auto-create admin. Use the browser setup at http://localhost:5005"
echo "  ✓ Redash database initialised"

# ---- Step 6: Start everything -----------------------------------------------
echo ""
echo "→ Starting all services ..."
docker compose up -d

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅  Setup Complete!                                         ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo "║  📊 Redash Dashboard:   http://localhost:5005                ║"
echo "║  📚 Ralph LRS:          http://localhost:8100                ║"
echo "║  🔍 Elasticsearch:      http://localhost:9200                ║"
echo "║                                                              ║"
echo "║  Ralph LRS Credentials:                                      ║"
echo "║    Username: ${RALPH_USER}                                           ║"
echo "║    Password: ${RALPH_PASS}                                          ║"
echo "║                                                              ║"
echo "║  Test Ralph:                                                  ║"
echo "║    curl http://localhost:8100/__heartbeat__                   ║"
echo "║                                                              ║"
echo "║  Test xAPI POST:                                              ║"
echo "║    curl -sL -w '%{http_code}' \\                              ║"
echo "║      -u ${RALPH_USER}:${RALPH_PASS} \\                                       ║"
echo "║      -H 'Content-Type: application/json' \\                   ║"
echo "║      http://localhost:8100/xAPI/statements \\                  ║"
echo "║      --data '[{...xapi statement...}]'                       ║"
echo "║                                                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

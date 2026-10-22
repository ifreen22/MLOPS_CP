#!/usr/bin/env bash
# ==============================================================================
# AIOps Sentinel - Production Setup Script for Linux, macOS & WSL
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\033[36m=========================================================================="
echo "AIOps Sentinel - Automated Linux / macOS / WSL Setup"
echo -e "==========================================================================\033[0m"

# 1. Prerequisite Checks
command -v python3 >/dev/null 2>&1 || { echo >&2 "[FAIL] Python 3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo >&2 "[FAIL] Node.js is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo >&2 "[FAIL] Docker is required but not installed."; exit 1; }

# 2. Environment Templates
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "[OK] Created root .env"
fi

if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
    cp "$SCRIPT_DIR/backend/.env.example" "$SCRIPT_DIR/backend/.env"
    echo "[OK] Created backend/.env"
fi

if [ ! -f "$SCRIPT_DIR/aiops-sentinel/.env" ]; then
    cp "$SCRIPT_DIR/aiops-sentinel/.env.example" "$SCRIPT_DIR/aiops-sentinel/.env"
    echo "[OK] Created aiops-sentinel/.env"
fi

# 3. Python Virtual Environment
VENV_PATH="$SCRIPT_DIR/backend/.venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment in $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
fi

echo "Installing backend dependencies..."
"$VENV_PATH/bin/python" -m pip install --upgrade pip --quiet
"$VENV_PATH/bin/python" -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet

# 4. Prisma Client Generation
echo "Generating Prisma Client..."
(cd "$SCRIPT_DIR/backend" && "$VENV_PATH/bin/python" -m prisma generate)

# 5. Frontend Dependencies & Build
echo "Building Frontend..."
(cd "$SCRIPT_DIR/aiops-sentinel" && npm install --legacy-peer-deps && npm run build)

# 6. Docker Stack Startup
echo "Starting Docker Compose stack..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d

echo "Waiting for PostgreSQL database readiness..."
sleep 10
(cd "$SCRIPT_DIR/backend" && npx prisma db push --accept-data-loss)

echo -e "\033[32m=========================================================================="
echo "SETUP COMPLETE! Run ./healthcheck.sh to verify services."
echo -e "==========================================================================\033[0m"

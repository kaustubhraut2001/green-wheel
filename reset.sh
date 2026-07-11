#!/bin/bash
# reset.sh — Wipes Docker volumes and restarts everything cleanly.
# Run this whenever Postgres reports "database system was not properly shut down".
#
# Usage:  bash reset.sh

set -e

echo "🛑  Stopping all containers..."
docker compose down --remove-orphans

echo "🗑️   Removing postgres volume (this deletes all data)..."
docker volume rm "green-wheels_postgres_data" 2>/dev/null || \
docker volume rm "green_wheels_postgres_data" 2>/dev/null || \
docker volume ls --filter name=postgres_data -q | xargs -r docker volume rm

echo "🔨  Rebuilding and starting..."
docker compose up --build -d

echo ""
echo "✅  Done. Services are starting..."
echo "   Backend API  → http://localhost:8000"
echo "   Frontend UI  → http://localhost:3000"
echo "   Swagger docs → http://localhost:8000/docs"
echo "   Flower       → http://localhost:5555"
echo ""
echo "📋  Watch logs: docker compose logs -f backend"

#!/usr/bin/env bash
set -euo pipefail

git fetch origin main
git checkout main
git pull --ff-only origin main

docker compose -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps

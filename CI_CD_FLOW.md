# CI/CD Workflow

This document describes the intended development and deployment flow for the portfolio workspace.

## Overview

```text
feature branch
  -> pull request
  -> CI checks pass
  -> merge into main
  -> GitHub Actions deploys to AWS Lightsail
```

The goal is to keep `main` deployable. Feature work should be reviewed through a pull request before it reaches production.

## 1. Develop on a Feature Branch

Start from the latest `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/update-portfolio
```

Make changes, then commit and push the branch:

```bash
git add -A
git commit -m "Update portfolio section"
git push origin feature/update-portfolio
```

## 2. Open a Pull Request

Open a pull request on GitHub:

```text
feature/update-portfolio -> main
```

This triggers `.github/workflows/ci.yml`.

## 3. CI Checks

The CI workflow runs on pull requests and pushes to `main`.

It performs:

```text
checkout repository
copy .env.example .env
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py check
docker compose run --rm cqcalling python manage.py check
docker compose run --rm primerqc python manage.py check
docker compose run --rm web python manage.py test reports
docker compose down -v
```

The CI job verifies:

- Health Risk Assessment Report System can pass Django checks.
- CqCalling can pass Django checks.
- PrimerQC can pass Django checks.
- Health Risk report workflow tests pass.

## 4. Merge Into Main

After CI passes, merge the pull request into `main`.

The merge triggers CI again on `main`. If that CI run succeeds, the deployment workflow starts.

## 5. Automatic Deployment

`.github/workflows/deploy.yml` runs after the `CI` workflow succeeds on `main`.

GitHub Actions connects to the Lightsail server by SSH and runs:

```bash
cd "$DEPLOY_PATH"
bash scripts/deploy.sh
```

The deploy script runs on the server:

```bash
git fetch origin main
git checkout main
git pull --ff-only origin main

docker compose -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

This updates the server code, rebuilds Docker images, and restarts the production services.

## 6. Production Services

The production stack uses `docker-compose.prod.yml`.

It starts:

```text
reverse-proxy  Caddy reverse proxy with automatic HTTPS
portfolio      static portfolio site
web            Health Risk Django app with Gunicorn
cqcalling      CqCalling Django app with Gunicorn
primerqc       PrimerQC Django app with Gunicorn
db             PostgreSQL
```

Domain routing is planned as:

```text
hunglin-dev.com             Portfolio
www.hunglin-dev.com         Portfolio
health.hunglin-dev.com      Health Risk Assessment Report System
cqcalling.hunglin-dev.com   CqCalling
primerqc.hunglin-dev.com    PrimerQC
```

## 7. Required GitHub Secrets

Configure these in GitHub:

```text
Settings -> Secrets and variables -> Actions
```

Required secrets:

| Secret | Purpose |
| --- | --- |
| `LIGHTSAIL_HOST` | Lightsail Static IP. |
| `LIGHTSAIL_USER` | SSH username, usually `ubuntu`. |
| `LIGHTSAIL_SSH_KEY` | Private SSH key content for server access. |
| `DEPLOY_PATH` | Repository path on the server, for example `/home/ubuntu/portfolio`. |

Never commit private keys or production secrets to the repository.

## 8. First Server Setup

Before automatic deployment can work, the Lightsail server must be prepared once:

1. Install Docker and Docker Compose.
2. Clone the repository to `DEPLOY_PATH`.
3. Create `.env.production` from `.env.production.example`.
4. Replace all placeholder secrets and domain values.
5. Update `.env.production` with the real domain names used by Caddy:

```text
PORTFOLIO_DOMAINS=hunglin-dev.com, www.hunglin-dev.com
HEALTH_DOMAIN=health.hunglin-dev.com
CQCALLING_DOMAIN=cqcalling.hunglin-dev.com
PRIMERQC_DOMAIN=primerqc.hunglin-dev.com
```

6. Confirm the server firewall allows inbound TCP 80 and 443.
7. Run the first deployment manually:

```bash
bash scripts/deploy.sh
```

After the manual deployment works, GitHub Actions can handle future deployments.

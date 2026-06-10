# Deployment Preparation

This project is ready to deploy as a single Docker Compose workspace on a VPS such as AWS Lightsail.

## Recommended First Deployment

Use one Ubuntu server with Docker and Docker Compose:

- Portfolio: `www.yourdomain.com`
- Health Risk Assessment Report System: `health.yourdomain.com`
- CqCalling: `cqcalling.yourdomain.com`
- PrimerQC: `primerqc.yourdomain.com`

For AWS Lightsail, start with a 2GB instance. The stack runs three Django apps, one static portfolio, Nginx, and PostgreSQL.

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Local development compose file using Django `runserver`. |
| `docker-compose.prod.yml` | Production compose file using Gunicorn and no source bind mounts for Django apps. |
| `.env.example` | Local development environment example. |
| `.env.production.example` | Production environment template. Copy this to `.env.production` on the server. |
| `infrastructure/nginx/default.conf` | Subdomain reverse proxy configuration. |

## Server Setup

1. Create an AWS Lightsail Ubuntu instance.
2. Attach a Static IP.
3. Point DNS records to the Static IP:

```text
A     yourdomain.com          <STATIC_IP>
A     www.yourdomain.com      <STATIC_IP>
A     health.yourdomain.com   <STATIC_IP>
A     cqcalling.yourdomain.com <STATIC_IP>
A     primerqc.yourdomain.com <STATIC_IP>
```

4. Install Docker and Docker Compose on the server.
5. Clone the repository.
6. Copy the production env file:

```bash
cp .env.production.example .env.production
```

7. Edit `.env.production`:

- set `DJANGO_SECRET_KEY`, `CQCALLING_SECRET_KEY`, and `PRIMERQC_SECRET_KEY`
- set a strong `POSTGRES_PASSWORD`
- set a strong `DJANGO_SUPERUSER_PASSWORD`
- replace `yourdomain.com` with the real domain
- keep `DJANGO_DEMO_LOGIN_PREFILL=0`
- keep `CREATE_DEMO_USERS=0` for public deployment

8. Update `infrastructure/nginx/default.conf` and replace all `yourdomain.com` values with the real domain.

9. Build and start:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

10. Check service status and logs:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs web
docker compose -f docker-compose.prod.yml logs cqcalling
docker compose -f docker-compose.prod.yml logs primerqc
```

## HTTPS

The current production compose exposes HTTP through Nginx. Add HTTPS before sharing the site publicly.

Practical options:

- Put AWS Lightsail Load Balancer in front and attach an SSL certificate.
- Or install Certbot on the server and configure Nginx certificates.
- Or replace the reverse proxy with Caddy for automatic Let's Encrypt certificates.

After HTTPS is working, set these values in `.env.production`:

```text
DJANGO_SECURE_SSL_REDIRECT=1
CQCALLING_SECURE_SSL_REDIRECT=1
PRIMERQC_SECURE_SSL_REDIRECT=1
```

## Backup

Back up PostgreSQL and uploaded health-risk media before any server rebuild.

Database dump:

```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U healthrisk healthrisk > healthrisk_backup.sql
```

Media volume backup should include the Docker volume named `media_data`, which stores uploaded SNP files and generated PDF reports.

## Pre-Public Checklist

- `DEBUG=0` for all Django apps.
- Real production secrets are set.
- Demo passwords are not used publicly.
- Demo login pre-fill is disabled.
- `CREATE_DEMO_USERS=0`.
- DNS points to the server Static IP.
- Nginx `server_name` values match the real domain.
- HTTPS is configured before sending the URL to others.
- PostgreSQL and media backup process is documented.
- No confidential CSV or private training data is committed.

## CI/CD

The repository includes GitHub Actions for the basic production workflow:

```text
feature branch -> pull request -> CI passes -> merge main -> deploy to Lightsail
```

For the full step-by-step workflow, see `CI_CD_FLOW.md`.

### CI

`.github/workflows/ci.yml` runs on pull requests and pushes to `main`.

It performs:

- Docker image build
- Django check for Health Risk, CqCalling, and PrimerQC
- Health Risk report tests

### CD

`.github/workflows/deploy.yml` runs after the `CI` workflow succeeds on `main`.

It connects to the Lightsail instance by SSH and runs:

```bash
bash scripts/deploy.sh
```

The deploy script:

```text
git pull --ff-only origin main
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

### Required GitHub Secrets

Add these in GitHub:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Required secrets:

| Secret | Example | Purpose |
| --- | --- | --- |
| `LIGHTSAIL_HOST` | `12.34.56.78` | Lightsail Static IP. |
| `LIGHTSAIL_USER` | `ubuntu` | SSH username for Ubuntu Lightsail. |
| `LIGHTSAIL_SSH_KEY` | private key content | Private SSH key allowed to access the server. |
| `DEPLOY_PATH` | `/home/ubuntu/portfolio` | Repository path on the server. |

### Server Prerequisites

Before enabling automatic deployment:

1. SSH into the Lightsail instance.
2. Install Docker and Docker Compose.
3. Clone the repository to the value used by `DEPLOY_PATH`.
4. Create `.env.production` from `.env.production.example`.
5. Replace the placeholder domain and secrets.
6. Run the first deployment manually:

```bash
bash scripts/deploy.sh
```

After the manual deployment works, merging into `main` can trigger automatic deployment.

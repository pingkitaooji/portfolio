# Biomedical Portfolio

This repository is a Dockerized portfolio workspace that contains one portfolio entry page and three biomedical software demo projects.

## Projects

| Path | Site | Description |
| --- | --- | --- |
| `sites/portfolio` | Portfolio | Personal introduction, project showcase, skills, and contact entry page. |
| `sites/health-risk` | Health Risk Assessment Report System | Django system for SNP upload, automatic sample serial assignment, patient records, risk calculation, PDF report storage, and role-based access control. |
| `sites/CqCalling` | CqCalling | Django + Python qPCR signal analysis demo for 40-cycle fluorescence input, sigmoid fitting, Cq calling, QC metrics, and JSON output. |
| `sites/PrimerQC` | PrimerQC | Django + Python primer pair quality prediction demo using Primer3-style features and a pre-trained model artifact. |

## Architecture

```text
.
├── sites/
│   ├── portfolio/       Static portfolio entry site
│   ├── health-risk/     Django health risk report system
│   ├── CqCalling/       Django qPCR Cq calling demo
│   └── PrimerQC/        Django primer prediction demo
├── infrastructure/
│   └── nginx/           Reverse proxy configuration
├── private_data/        Local-only confidential data, ignored by Git
├── docker-compose.yml
├── .env.example
└── README.md
```

## Tech Stack

- Backend: Python, Django, PHP/Laravel experience represented in portfolio skills
- Data and algorithms: Python data processing, qPCR signal analysis, primer feature scoring, SNP workflow simulation
- Deployment: Docker Compose, Gunicorn, Nginx, Linux, AWS-oriented deployment planning
- Database: PostgreSQL in Docker for the health-risk system; SQLite fallback for local standalone Django runs

## Local Run

1. Create an environment file:

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

2. Start all services:

```bash
docker compose up -d --build
```

3. Open the local sites:

| Service | URL |
| --- | --- |
| Portfolio | `http://127.0.0.1/` |
| Health Risk System | `http://127.0.0.1:8000/` |
| CqCalling | `http://127.0.0.1:8002/` |
| PrimerQC | `http://127.0.0.1:8003/` |

Health Risk demo accounts are created by the container entrypoint when using the demo environment:

```text
clinic_admin / demo123
hospital_a / demo123
hospital_b / demo123
hospital_c / demo123
```

The Health Risk login page can be pre-filled with `clinic_admin / demo123` for local demo use. Disable this in production with `DJANGO_DEMO_LOGIN_PREFILL=0`. SNP uploads use an automatically assigned sample serial number and do not require an instrument code field.

## Deployment

Production preparation files are included:

- `docker-compose.prod.yml` runs the Django apps with Gunicorn.
- `.env.production.example` lists the required production environment variables.
- `DEPLOYMENT.md` contains the AWS Lightsail/VPS deployment and CI/CD checklist.

## Domain Layout

The reverse proxy is designed for this deployment layout:

```text
www.yourdomain.com        Portfolio
health.yourdomain.com     Health Risk Assessment Report System
cqcalling.yourdomain.com  CqCalling
primerqc.yourdomain.com   PrimerQC
```

The local Docker setup exposes each service through direct ports for development, while `infrastructure/nginx/default.conf` documents the subdomain routing model.

## Data Safety

Confidential training data is not committed.

- `private_data/` is ignored by Git.
- The de-identified primer CSV is kept outside committed project paths.
- `.env`, local databases, media uploads, logs, static build outputs, and cache files are ignored.
- PrimerQC commits only the demo model artifact needed by the web app, not the source confidential CSV.

## Useful Commands

```bash
docker compose ps
docker compose logs web
docker compose logs cqcalling
docker compose logs primerqc
docker compose down
```

Run Django checks inside a service:

```bash
docker compose exec web python manage.py check
docker compose exec cqcalling python manage.py check
docker compose exec primerqc python manage.py check
```

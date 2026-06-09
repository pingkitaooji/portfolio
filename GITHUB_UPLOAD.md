# GitHub Upload Guide

This project is ready to publish as a GitHub portfolio repository.

## Safety Checklist

Before pushing:

- `.env` is ignored.
- `private_data/` is ignored.
- SQLite databases are ignored.
- Generated `media/` and `staticfiles/` folders are ignored.
- The confidential PrimerQC CSV is ignored:
  `**/2_UMU_primer_Tm_info_json_deidentified_2.csv`

The PrimerQC training CSV has been moved to:

```text
private_data/PrimerQC/
```

Do not upload that folder to GitHub.

## Option A: Publish The Whole Portfolio

Use this if you want one repository containing:

- `sites/portfolio`
- `sites/health-risk`
- `sites/CqCalling`
- `sites/PrimerQC`
- Docker Compose and Nginx config

Create an empty GitHub repository first, then run:

```bash
git init
git add .
git status
git commit -m "Initial portfolio project"
git branch -M main
git remote add origin https://github.com/pingkitaooji/portfolio.git
git push -u origin main
```

## Option B: Publish Three Project Repositories Separately

Use this if you want each project to have its own GitHub repository.

### Health Risk

```bash
cd sites/health-risk
git init
git add .
git commit -m "Initial health risk assessment system"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/health-risk-assessment-system.git
git push -u origin main
```

### CqCalling

```bash
cd sites/CqCalling
git init
git add .
git commit -m "Initial CqCalling project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/cqcalling.git
git push -u origin main
```

### PrimerQC

```bash
cd sites/PrimerQC
git init
git add .
git commit -m "Initial PrimerQC project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/primerqc.git
git push -u origin main
```

## Local Requirement

This machine currently does not expose the `git` command in the terminal. Install Git for Windows first:

```text
https://git-scm.com/download/win
```

After Git is installed, restart the terminal and run:

```bash
git --version
```

Then run the upload commands above.

## Update Portfolio GitHub Links

After creating the repositories, replace these placeholder links in:

```text
sites/portfolio/index.html
README.md
```

Current placeholders:

```text
https://github.com/pingkitaooji/portfolio
```

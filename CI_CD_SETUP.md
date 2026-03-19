# CI/CD Setup Guide

This project uses a GitHub Actions workflow at `.github/workflows/ci.yml`.

## What the pipeline does

On pull requests and pushes:
1. Frontend CI: install, lint, build, dependency audit.
2. Backend CI: install, Django checks, tests, Bandit, pip-audit.
3. Secret scan: Gitleaks.

On push to `main`:
1. Trigger backend deployment hook (if configured).
2. Trigger frontend deployment hook (if configured).
3. Run post-deploy backend health check (if configured).
4. Verify frontend URL is reachable (if configured).

## Required repository secrets

Set these in GitHub repository settings -> Secrets and variables -> Actions.

Optional deployment secrets (CD stage):
- `BACKEND_DEPLOY_HOOK_URL`
- `FRONTEND_DEPLOY_HOOK_URL`
- `BACKEND_HEALTHCHECK_URL` (for example: `https://your-api-domain/api/health/`)
- `FRONTEND_URL` (for example: `https://your-frontend-domain/`)

If deploy secrets are not set, CI still runs and deploy steps are skipped.

## Local checks before pushing

Backend:
- `cd backend`
- `..\.venv\Scripts\python.exe manage.py check`
- `..\.venv\Scripts\python.exe manage.py test`

Frontend:
- `cd frontend`
- `npm run lint`
- `npm run build`

## Evidence to capture for NCI report/video

1. PR run showing frontend + backend + secret scan jobs passing.
2. Push to `main` showing deploy job execution.
3. Health check step passing after deployment.
4. Public frontend URL and backend health URL accessible.
5. One code change from IDE -> commit -> push -> pipeline -> deployed result.

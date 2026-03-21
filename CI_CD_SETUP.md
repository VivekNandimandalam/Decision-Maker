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

AWS deployment secrets (CD stage):
- `AWS_REGION`
- `AWS_ROLE_TO_ASSUME`
- `S3_BUCKET_FRONTEND`
- `CLOUDFRONT_DISTRIBUTION_ID`
- `EB_APPLICATION_NAME`
- `EB_ENVIRONMENT_NAME`
- `EB_DEPLOY_BUCKET`
- `BACKEND_HEALTHCHECK_URL` (for example: `https://your-api-domain/api/health/`)
- `FRONTEND_URL` (for example: `https://your-frontend-domain/`)

If AWS deploy secrets are not set, CI still runs and AWS deploy steps are skipped.

## Required Elastic Beanstalk environment variables

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_ENGINE=postgres`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_SSLMODE=require`
- `REDIS_URL`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`

Redis must be reachable from Elastic Beanstalk for Channels realtime updates. The backend now serves ASGI through Daphne and expects WebSocket traffic to reach `/ws/`.

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

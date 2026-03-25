# Pre-Deployment Checklist & Production Setup Guide

## 🔐 SECURITY VALIDATION CHECKLIST

### Backend Security
- [ ] `DEBUG = False` in production settings
- [ ] `ALLOWED_HOSTS` configured with actual domain names
- [ ] `SECRET_KEY` is long random string (50+ chars), stored in secrets manager
- [ ] CSRF protection enabled: `CSRF_MIDDLEWARE` in MIDDLEWARE
- [ ] CORS configured to specific origin(s) only (not `*`)
- [ ] Database credentials stored in AWS Secrets Manager (not in code)
- [ ] All database queries use Django ORM (prevents SQL injection)
- [ ] API rate limiting enabled (20 req/min for poll creation, 30 req/min for voting)
- [ ] HTTPS enforced: `SECURE_SSL_REDIRECT = True`
- [ ] Security headers configured:
  - [ ] X-Frame-Options: DENY
  - [ ] X-Content-Type-Options: nosniff
  - [ ] X-XSS-Protection: 1; mode=block
- [ ] HSTS enabled: `SECURE_HSTS_SECONDS = 31536000`
- [ ] Session cookies: Secure, HttpOnly, SameSite=Lax
- [ ] No sensitive data in logs
- [ ] API endpoints require authentication (device token validation)

### Frontend Security
- [ ] No hardcoded API keys or credentials
- [ ] API base URL environment variable
- [ ] CORS credentials: `credentials: 'include'` for cookie transmission
- [ ] Input validation on all forms
- [ ] No XSS vulnerabilities (using React's built-in XSS protection)
- [ ] Content Security Policy headers on CloudFront

### Database Security
- [ ] RDS instance not publicly accessible
- [ ] Security group restricts access (EB only)
- [ ] Master password strong (20+ chars, mixed case, numbers, symbols)
- [ ] Automated backups enabled (30-day retention)
- [ ] Multi-AZ enabled for high availability
- [ ] Encryption at rest enabled
- [ ] SSL/TLS required for connections

### Infrastructure Security
- [ ] VPC configured with private subnets for database
- [ ] Security groups follow least-privilege principle
- [ ] IAM roles/policies minimal permissions
- [ ] CloudFront restricts origin to S3 (via OAI)
- [ ] API Gateway (if used) requires API keys
- [ ] CloudWatch logs encrypted

---

## ✅ FUNCTIONALITY VALIDATION CHECKLIST

### Backend Functionality
- [ ] All Django migrations applied
- [ ] Database schema matches models
- [ ] API endpoints working:
  - [ ] `GET /api/polls/` - List all polls
  - [ ] `POST /api/polls/create/` - Create poll
  - [ ] `GET /api/polls/{id}/` - Get poll details with voting status
  - [ ] `POST /api/polls/{id}/vote/` - Submit vote
  - [ ] `GET /health/` - Health check
- [ ] Vote deduplication working:
  - [ ] First vote returns 201 Created
  - [ ] Second vote from same device returns 409 Conflict
- [ ] Device token cookie created & persisted
- [ ] Device token hashing working correctly
- [ ] Logging showing device token, vote attempts, errors
- [ ] Error responses include proper status codes

### Frontend Functionality
- [ ] Build successful: `npm run build` completes
- [ ] No TypeScript errors: `npm run type-check`
- [ ] No console errors in browser DevTools
- [ ] Poll list loads correctly
- [ ] Create poll form works
- [ ] Vote submission works
- [ ] "Already voted" state shows correctly
- [ ] Vote button disabled after voting
- [ ] Real-time updates work (2-second polling)
- [ ] Works across multiple tabs/windows
- [ ] Responsive design on mobile/tablet/desktop

### Integration Tests
- [ ] Create poll → See in list (within 2 seconds)
- [ ] Vote on poll → Vote counted (within 2 seconds)
- [ ] Vote from second browser tab → Shows as already voted
- [ ] Refresh page → Vote state persists
- [ ] Close browser → Reopen → Still voted (cookie persists)

---

## 📋 PRE-DEPLOYMENT TECHNICAL CHECKLIST

### Backend Preparation
- [ ] Update `requirements.txt` with production packages:
  ```
  psycopg2-binary==2.9.11   # PostgreSQL driver
  gunicorn==25.0.0          # Production server
  whitenoise==6.6.0         # Static file serving
  python-decouple==3.8      # Env var management
  ```
- [ ] Update `settings.py`:
  - [ ] Add PostgreSQL database configuration with `dj_database_url`
  - [ ] Add S3 static file configuration
  - [ ] Add CloudFront domain
  - [ ] Add security settings (see above)
  - [ ] Add logging configuration for CloudWatch
- [ ] Create `Dockerfile` (provided)
- [ ] Create `.dockerignore` file
- [ ] Test locally with PostgreSQL:
  ```bash
  docker-compose up -d db
  export DATABASE_URL=postgresql://admin:password@localhost/polling_db
  python manage.py migrate
  python manage.py runserver
  ```

### Frontend Preparation
- [ ] Update API base URL environment variable
- [ ] Add analytics tracking (Google Analytics, Sentry, etc.)
- [ ] Optimize images (use WebP format)
- [ ] Minify CSS/JS (automatic with Vite)
- [ ] Build test:
  ```bash
  npm run build
  npm run preview  # Preview production build locally
  ```

### AWS Account Setup
- [ ] Create AWS account
- [ ] Create IAM user for deployment
- [ ] Grant permissions:
  - [ ] Elastic Beanstalk
  - [ ] RDS
  - [ ] S3
  - [ ] CloudFront
  - [ ] CloudWatch
  - [ ] Secrets Manager
  - [ ] IAM (for role creation)
- [ ] Configure AWS CLI:
  ```bash
  aws configure
  aws sts get-caller-identity  # Verify credentials
  ```

### Environment Variables
- [ ] Create `.env.production` from `.env.production.example`
- [ ] Generate strong `DJANGO_SECRET_KEY`:
  ```bash
  python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
  ```
- [ ] Store in AWS Secrets Manager (NOT in code repo)
- [ ] Document all variables for future reference

---

## 🚀 DEPLOYMENT STAGE CHECKLIST

### Stage 1: Database Setup
- [ ] Create RDS PostgreSQL instance (see AWS_DEPLOYMENT_GUIDE.md)
- [ ] Document connection string
- [ ] Create security group allowing EB instance only
- [ ] Verify connectivity
- [ ] Create database/user
- [ ] Enable automated backups
- [ ] Enable Multi-AZ

### Stage 2: Storage Setup
- [ ] Create S3 bucket for static files
- [ ] Enable versioning
- [ ] Enable encryption
- [ ] Create CloudFront distribution
- [ ] Document bucket name & CloudFront domain

### Stage 3: Backend Deployment
- [ ] Initialize Elastic Beanstalk:
  ```bash
  cd backend
  eb init -p python-3.12 polling-app-backend
  ```
- [ ] Create environment:
  ```bash
  eb create production --instance-type t3.small
  ```
- [ ] Configure environment variables (via AWS Console or CLI)
- [ ] Deploy application:
  ```bash
  eb deploy
  ```
- [ ] Run migrations:
  ```bash
  eb ssh
  python manage.py migrate
  exit
  ```
- [ ] Verify application is running:
  ```bash
  curl https://polling-app-backend.elasticbeanstalk.com/health/
  ```

### Stage 4: Frontend Deployment
- [ ] Build frontend:
  ```bash
  cd frontend
  npm run build
  ```
- [ ] Upload to S3:
  ```bash
  aws s3 sync dist/ s3://polling-app-static/ --delete
  ```
- [ ] Invalidate CloudFront cache:
  ```bash
  aws cloudfront create-invalidation --distribution-id D111111 --paths "/*"
  ```
- [ ] Verify deployment:
  ```bash
  curl https://yourdomain.com
  ```

---

## 🧪 POST-DEPLOYMENT TESTING

### Functional Testing
- [ ] Create a poll in production
- [ ] Vote on the poll from browser 1
- [ ] Open same poll in browser 2 (different device/incognito)
- [ ] Attempt to vote from browser 2 (should be allowed - different device)
- [ ] Vote from browser 1 again (should show 409 Conflict)
- [ ] Refresh browser 1 (should still show as voted)
- [ ] Check CloudWatch logs for errors
- [ ] Verify metrics (latency, error rate, throughput)

### Security Testing
- [ ] Test HTTPS redirects HTTP requests
- [ ] Test CORS with invalid origin (should fail)
- [ ] Test CSRF protection (invalid token should fail)
- [ ] Check security headers with online tool (securityheaders.com)
- [ ] Run OWASP ZAP scan for vulnerabilities
- [ ] Verify no sensitive data in logs

### Load Testing
- [ ] Use Apache JMeter to simulate load (100+ concurrent users)
- [ ] Verify response times < 500ms under load
- [ ] Verify error rate < 1%
- [ ] Check database connection pool doesn't exhaust
- [ ] Monitor CloudWatch during test

---

## 📊 MONITORING SETUP

### CloudWatch Dashboards
Create dashboard with:
- Application response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Request count
- Database query time
- CPU utilization
- Memory utilization
- Disk space

### Alarms
- [ ] HTTP 5xx errors > 5% → Send SNS notification
- [ ] Response time p95 > 1000ms → Send SNS notification
- [ ] Database CPU > 80% → Send SNS notification
- [ ] Database connections > threshold → Send SNS notification
- [ ] Disk space < 10% → Send SNS notification

---

## 📝 DOCUMENTATION UPDATES

- [ ] Update README.md with production deployment steps
- [ ] Document API endpoints with examples
- [ ] Create troubleshooting guide
- [ ] Document scaling procedures
- [ ] Create incident response runbook
- [ ] Document backup/restore procedures
- [ ] Create cost optimization guidelines

---

## 🔄 CI/CD PIPELINE (GitHub Actions)

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build & Test Backend
        run: |
          cd backend
          pip install -r requirements.txt
          python manage.py test
          python manage.py makemigrations --check
      
      - name: Build & Test Frontend
        run: |
          cd frontend
          npm ci
          npm run build
          npm run type-check
      
      - name: Deploy to AWS
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          cd backend
          eb deploy production
```

---

## 🎯 FINAL VERIFICATION

Before marking as production-ready:
- [ ] All tests passing
- [ ] No TypeScript errors
- [ ] No console warnings
- [ ] All security checks passing
- [ ] Performance acceptable (< 500ms response time)
- [ ] Monitoring & alerting configured
- [ ] Backup procedures documented & tested
- [ ] Incident response plan documented
- [ ] Team trained on deployment procedures
- [ ] Compliance requirements met

---

**Status**: Ready for AWS Deployment
**Last Updated**: 2025-03-25
**Next Steps**: Execute deployment following AWS_DEPLOYMENT_GUIDE.md

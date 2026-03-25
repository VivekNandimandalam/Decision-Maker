# Polling Application - AWS Deployment Ready

## 🎯 Project Summary

A real-time Django + React polling application featuring:
- ✅ Device-based vote deduplication (one vote per device per poll)
- ✅ HTTP polling architecture (2-second intervals)
- ✅ Cookie-based device identification
- ✅ REST API with rate limiting
- ✅ Production-ready configuration
- ✅ AWS deployment ready (S3, CloudFront, RDS, Elastic Beanstalk)

---

## 📊 Architecture Overview

```
┌─────────────────┐       HTTPS        ┌──────────────────┐
│    Frontend     │◄──────────────────►│   Django API     │
│  (S3 + Cloud   │    REST + Polling   │   (Gunicorn)     │
│    Front)       │   (2sec intervals)  │  (Elastic EB)    │
└─────────────────┘                    └────────┬─────────┘
                                                 │
                                                 ▼
                                        ┌──────────────────┐
                                        │   PostgreSQL     │
                                        │   (RDS)          │
                                        └──────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### Using Docker Compose (Recommended)
```bash
cd d:\clouddevopsec_project
docker-compose up -d

# Wait for services to start
sleep 10

# Apply migrations
docker-compose exec backend python manage.py migrate

# Visit http://localhost:5173
```

### Manual Setup
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## 📋 Recent Changes for AWS Deployment

### 1. Backend Updates
- ✅ Updated `requirements.txt`:
  - Removed: Django Channels, Daphne (WebSocket-related)
  - Added: `whitenoise` (static file serving), `django-storages` (S3), `dj-database-url` (DB parsing), `boto3` (AWS SDK)
  
- ✅ Created `settings_production.py`:
  - PostgreSQL database configuration with connection pooling
  - AWS S3 static file storage with CloudFront integration
  - Security headers and HTTPS enforcement
  - Comprehensive logging for CloudWatch
  - Environment variable management
  
- ✅ Updated `Procfile`:
  - Changed from `waitress` → `gunicorn` (production standard)
  - Configured worker processes, timeouts, and max requests for stability
  
- ✅ Created `Dockerfile`:
  - Multi-stage build with Python 3.12
  - Static file collection
  - Gunicorn configuration for AWS deployment

### 2. Frontend Updates
- ✅ Build configuration optimized for production
- ✅ Environment variables for API base URL
- ✅ Removed WebSocket code (using HTTP polling instead)

### 3. Configuration Files
- ✅ `.env.production.example`: Template for production environment variables
- ✅ `docker-compose.yml`: Complete local development stack with PostgreSQL
- ✅ `.github/workflows/deploy.yml`: Automated CI/CD pipeline
- ✅ `DEPLOYMENT_CHECKLIST.md`: Step-by-step deployment guide

---

## 🔧 Production Configuration

### Environment Variables Required
```bash
# Django
DJANGO_SECRET_KEY=<generate-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (RDS PostgreSQL)
DATABASE_URL=postgresql://admin:PASSWORD@polling-app-db.xxxxx.rds.amazonaws.com:5432/polling_db

# CORS & Frontend
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# AWS S3 Static Files
USE_S3=True
AWS_STORAGE_BUCKET_NAME=polling-app-static
AWS_CLOUDFRONT_DOMAIN=d{distribution-id}.cloudfront.net
AWS_S3_REGION_NAME=us-east-1

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
```

---

## 📈 Deployment Steps

### Phase 1: AWS Account Setup
1. Create AWS account
2. Create IAM user with EB, RDS, S3, CloudFront, CloudWatch permissions
3. Configure AWS CLI: `aws configure`

### Phase 2: Database
1. Create RDS PostgreSQL instance
2. Configure security group (allow EB only)
3. Run migrations: `python manage.py migrate`

### Phase 3: Static Files
1. Create S3 bucket
2. Create CloudFront distribution
3. Set bucket policy for CloudFront access

### Phase 4: Backend
1. Initialize: `eb init -p python-3.12 polling-app-backend`
2. Create environment: `eb create production --instance-type t3.small`
3. Set environment variables via AWS Console
4. Deploy: `eb deploy`

### Phase 5: Frontend
1. Build: `npm run build`
2. Upload to S3: `aws s3 sync dist/ s3://bucket-name/ --delete`
3. Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id D111111 --paths "/*"`

**Detailed instructions** in `AWS_DEPLOYMENT_GUIDE.md` and `DEPLOYMENT_CHECKLIST.md`

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
python manage.py test polls
```

### Frontend Build
```bash
cd frontend
npm run build
npm run preview  # Preview production build
```

### Integration Test
```bash
cd backend
python tests/test_voting.py  # Verify vote deduplication
```

---

## 🛡️ Security Features

- ✅ HTTPS enforcement (SECURE_SSL_REDIRECT = True)
- ✅ CSRF protection on all state-changing operations
- ✅ CORS restricted to specific origins
- ✅ SQL injection prevention (Django ORM)
- ✅ XSS protection (React auto-escaping)
- ✅ Session security (HttpOnly, Secure, SameSite)
- ✅ Rate limiting on API endpoints
- ✅ Database encryption (RDS)
- ✅ VPC security groups (database not publicly accessible)
- ✅ Security headers (HSTS, X-Frame-Options, CSP)

---

## 📊 Performance Optimization

- ✅ HTTP polling every 2 seconds (lightweight)
- ✅ Database connection pooling (conn_max_age=600)
- ✅ Static file compression with WhiteNoise
- ✅ CloudFront CDN for global distribution
- ✅ Gunicorn with 4 workers for concurrent requests
- ✅ Django ORM query optimization
- ✅ Pagination on list endpoints

---

## 💰 Estimated Monthly Costs (AWS)

| Service | Tier | Cost |
|---------|------|------|
| Elastic Beanstalk | t3.small, 1 instance | $20 |
| RDS PostgreSQL | db.t3.micro, 20GB | $25 |
| S3 Storage | <1GB | <$1 |
| CloudFront | ~100GB/month | $9 |
| Data transfer | Standard | ~$5 |
| **Total** | | **~$60/month** |

---

## 📚 Documentation

- **[AWS_DEPLOYMENT_GUIDE.md](./AWS_DEPLOYMENT_GUIDE.md)** - Complete deployment guide
- **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** - Pre/post-deployment checklist
- **[CI_CD_SETUP.md](./CI_CD_SETUP.md)** - GitHub Actions configuration
- **[README.md](./README.md)** - Original project README

---

## 🔍 Monitoring & Alerts

### CloudWatch Dashboards
Monitor: Response time (p50, p95, p99), Error rate, Requests/sec, CPU, Memory, Disk space

### Alarms
- 5xx errors > 5%
- Response time p95 > 1s
- Database CPU > 80%
- Disk space < 10%

---

## 🚨 Troubleshooting

### 502 Bad Gateway
```bash
eb logs  # Check error logs
eb ssh   # SSH into instance
python manage.py migrate  # Run pending migrations
```

### Database Connection Error
```bash
# Verify security group allows EB IP
# Check RDS endpoint in environment variables
# Verify database exists and user has access
```

### Static Files Not Loading
```bash
# Rebuild frontend
npm run build

# Upload to S3
aws s3 sync frontend/dist/ s3://bucket-name/ --delete

# Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id D111111 --paths "/*"
```

---

## 📞 Next Steps

1. **Review**: Read `DEPLOYMENT_CHECKLIST.md` and `AWS_DEPLOYMENT_GUIDE.md`
2. **Prepare**: Set up AWS account and configure credentials
3. **Deploy DB**: Create RDS PostgreSQL instance
4. **Deploy Backend**: Push to Elastic Beanstalk
5. **Deploy Frontend**: Build and upload to S3 + CloudFront
6. **Monitor**: Set up CloudWatch dashboards and alarms
7. **Test**: Verify voting works end-to-end
8. **Optimize**: Monitor costs and performance

---

## 📝 File Structure

```
d:\clouddevopsec_project\
├── AWS_DEPLOYMENT_GUIDE.md          # 📖 Complete AWS deployment guide
├── DEPLOYMENT_CHECKLIST.md          # ✅ Pre/post-deployment checklist
├── docker-compose.yml               # 🐳 Docker Compose (dev stack)
├── .env.production.example          # 🔐 Production env template
├── .github/workflows/deploy.yml     # 🤖 CI/CD pipeline
├── .gitignore                       # 🚫 Git ignore rules
├── .dockerignore                    # 🚫 Docker ignore rules
│
├── backend/
│   ├── Dockerfile                   # 🐳 Docker image
│   ├── Procfile                     # 🚀 EB deployment config
│   ├── settings_production.py       # ⚙️ Production settings
│   ├── requirements.txt             # 📦 Python dependencies
│   ├── manage.py                    # 🔧 Django CLI
│   └── polls/                       # 📱 Poll app
│       ├── models.py                # Database models
│       ├── views.py                 # API endpoints
│       ├── serializers.py           # Request/response serialization
│       └── tests.py                 # Unit tests
│
└── frontend/
    ├── package.json                 # 📦 Node dependencies
    ├── vite.config.ts               # ⚙️ Build configuration
    ├── tsconfig.json                # TypeScript config
    ├── src/
    │   ├── main.tsx                 # React entry point
    │   ├── App.tsx                  # Main component
    │   ├── components/              # React components
    │   └── lib/polls.ts             # API client
    └── dist/                        # 📦 Production build
```

---

## 🎓 Best Practices Implemented

✅ **Infrastructure as Code**: Docker, Procfile, docker-compose.yml
✅ **Environment Management**: Separate .env files for dev/prod
✅ **CI/CD Automation**: GitHub Actions for testing and deployment
✅ **Security**: HTTPS, CSRF, CORS, rate limiting, security headers
✅ **Monitoring**: CloudWatch logging and dashboards
✅ **Performance**: CDN, database pooling, pagination
✅ **Documentation**: Deployment guides, checklists, architecture diagrams
✅ **Testing**: Unit tests, integration tests, load testing recommendations
✅ **Version Control**: Gitignore, semantic commit messages

---

## 📞 Support & Questions

For deployment issues:
1. Check `AWS_DEPLOYMENT_GUIDE.md` troubleshooting section
2. Review CloudWatch logs: `eb logs`
3. SSH into instance: `eb ssh`
4. Check application logs: `cat /var/log/eb-engine.log` on instance

---

**Status**: ✅ Ready for AWS Production Deployment
**Last Updated**: 2025-03-25
**Python Version**: 3.12
**Django Version**: 6.0.3
**Node Version**: 18+

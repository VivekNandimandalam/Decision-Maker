# Polling Application - Complete Code Structure & AWS Deployment Guide

## 📊 PART 1: CODE STRUCTURE ANALYSIS

### Backend Structure (`d:\clouddevopsec_project\backend\`)
```
backend/
├── backend/                    # Django project configuration
│   ├── settings.py            # Configuration (DB, CORS, Logging, Security)
│   ├── urls.py                # API routes
│   ├── wsgi.py                # WSGI application entry point
│   └── asgi.py                # ASGI configuration
├── polls/                      # Poll application
│   ├── models.py              # Database models (Poll, PollOption, VoteRecord)
│   ├── views.py               # API endpoints (CRUD, voting)
│   ├── serializers.py         # Django REST serializers
│   ├── urls.py                # Poll-specific routes
│   ├── consumers.py           # WebSocket consumers (DISABLED - using polling)
│   ├── routing.py             # WebSocket routes (DISABLED)
│   └── migrations/            # Database migrations
├── manage.py                   # Django management CLI
├── Procfile                    # AWS Elastic Beanstalk config
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables (SECRET)

Database: SQLite (dev) → RDS PostgreSQL (prod)
Server: Django dev server (dev) → Gunicorn (prod)
```

### Frontend Structure (`d:\clouddevopsec_project\frontend\`)
```
frontend/
├── src/
│   ├── components/
│   │   ├── CreatePoll.tsx     # Poll creation form
│   │   ├── MyPolls.tsx        # User's polls list
│   │   └── PollPage.tsx       # Poll voting interface (FIXED ✓)
│   ├── lib/
│   │   └── polls.ts           # API client, utilities
│   ├── App.tsx                # Main app component
│   ├── App.css                # Styles
│   ├── main.tsx               # React entry point
│   └── vite-env.d.ts          # Vite types
├── index.html                 # HTML template
├── package.json               # Node dependencies
├── vite.config.ts             # Vite bundler config
└── tsconfig.json              # TypeScript config

Build: Vite (fast bundler)
Deployment: S3 + CloudFront (static hosting + CDN)
```

---

## 📋 PART 2: CURRENT IMPLEMENTATION STATUS

### ✅ Completed Features
- [x] Poll creation with unique shareable links
- [x] Device-based vote deduplication (HTTP cookie + device hash)
- [x] Real-time updates via HTTP polling (2-second intervals)
- [x] Vote blocking at database & application level
- [x] CORS configured for localhost:5173 ↔ localhost:8000
- [x] Rate limiting (20/m for poll creation, 30/m for voting)
- [x] Logging configured (Django + Python logging)
- [x] Database migrations working
- [x] Environment variable support (.env files)

### 🔧 Architecture
- **Frontend**: React + TypeScript + Vite (modern, fast)
- **Backend**: Django REST Framework + SQLite (dev)
- **Communication**: RESTful API (HTTP) + HTTP polling
- **Database**: SQLite (dev) → RDS PostgreSQL (prod)
- **Authentication**: Device token in HTTP-only cookie (no user login required)

---

## 🚀 PART 3: AWS DEPLOYMENT ARCHITECTURE

### Recommended AWS Stack
```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (S3 + CloudFront)                 │
│  - React app built with Vite                                   │
│  - Static files stored in S3                                   │
│  - Cached globally via CloudFront CDN                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│           Backend (Elastic Beanstalk or ECS/Fargate)           │
│  - Django application running on Gunicorn                      │
│  - Auto-scaling based on CPU/memory                            │
│  - Load balancer for traffic distribution                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│              Database (RDS PostgreSQL)                          │
│  - Managed relational database                                 │
│  - Automatic backups & failover                                │
│  - VPC security groups for access control                      │
└─────────────────────────────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│         Additional Services (Optional but Recommended)           │
│  - CloudWatch: Logging & monitoring                            │
│  - SNS: Error notifications                                    │
│  - Secrets Manager: Store sensitive credentials                │
│  - Route 53: DNS management                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 PART 4: STEP-BY-STEP AWS DEPLOYMENT

### Phase 1: Preparation (Local Setup)

#### 1.1 Update requirements.txt
Add production dependencies:
```
psycopg2-binary==2.9.11      # PostgreSQL driver
gunicorn==25.1.0              # Production WSGI server
whitenoise==6.6.0             # Static file serving
python-decouple==3.8          # Env var management
```

#### 1.2 Update Django Settings for Production
- ALLOWED_HOSTS: Point to Elastic Beanstalk URL
- DEBUG: False in production
- DATABASES: Use RDS PostgreSQL
- STATIC_FILES: Use S3 + CloudFront
- SECURE_SSL_REDIRECT: True
- SESSION_COOKIE_SECURE: True

### Phase 2: AWS Account Setup

#### 2.1 Create AWS Account & IAM User
- Sign up for AWS (ec2.amazonaws.com)
- Create IAM user with permissions for:
  - Elastic Beanstalk
  - RDS
  - S3
  - CloudFront
  - CloudWatch

#### 2.2 Configure AWS CLI
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Format (json)
```

### Phase 3: Database Setup (RDS PostgreSQL)

#### 3.1 Create RDS Instance
1. Go to AWS RDS Console
2. Create database:
   - Engine: PostgreSQL 14+
   - DB instance identifier: `polling-app-db`
   - Master username: `admin`
   - Master password: Generate strong password
   - DB name: `polling_db`
   - Storage: 20 GB (gp2)
   - Multi-AZ: Yes (for high availability)
   - Publicly accessible: No (access via Elastic Beanstalk only)
   - Backup retention: 30 days

#### 3.2 Create DB Subnet & Security Group
- Allow inbound traffic: Port 5432 from Elastic Beanstalk public IPs
- Document connection string:
  ```
  postgresql://admin:PASSWORD@polling-app-db.xxxxx.rds.amazonaws.com:5432/polling_db
  ```

### Phase 4: Static Files & CDN (S3 + CloudFront)

#### 4.1 Create S3 Bucket
1. Go to S3 Console
2. Create bucket: `polling-app-static-{account-id}`
3. Block public access: Disable (we'll use CloudFront)
4. Enable versioning: Yes
5. Enable server-side encryption: AES-256

#### 4.2 Create CloudFront Distribution
1. Create distribution
2. Origin domain: S3 bucket
3. Restrict bucket access: Yes (use OAI)
4. Allowed HTTP methods: GET, HEAD, OPTIONS
5. Enable compression: Yes
6. Cache behavior:
   - Viewer protocol: Redirect HTTP to HTTPS
   - TTL: 3600 seconds (1 hour)

### Phase 5: Backend Deployment (Elastic Beanstalk)

#### 5.1 Initialize Elastic Beanstalk
```bash
cd backend
eb init -p python-3.12 polling-app-backend --region us-east-1
```

#### 5.2 Create Environment
```bash
eb create production \
  --instance-type t3.small \
  --scale 1
```

#### 5.3 Configure Environment Variables
```bash
eb setenv \
  DJANGO_DEBUG=False \
  DJANGO_SECRET_KEY='your-random-secret-key' \
  DATABASE_URL='postgresql://admin:PASSWORD@polling-app-db.xxxxx.rds.amazonaws.com:5432/polling_db' \
  CORS_ALLOWED_ORIGINS='https://yourdomain.com' \
  AWS_STORAGE_BUCKET_NAME='polling-app-static' \
  AWS_CLOUDFRONT_DOMAIN='d111111.cloudfront.net'
```

#### 5.4 Deploy Application
```bash
eb deploy
```

#### 5.5 Run Database Migrations
```bash
eb ssh
python manage.py migrate
python manage.py createsuperuser (optional)
exit
```

### Phase 6: Frontend Deployment (S3 + CloudFront)

#### 6.1 Build Frontend
```bash
cd frontend
npm run build
# Creates dist/ folder with optimized files
```

#### 6.2 Upload to S3
```bash
aws s3 sync dist/ s3://polling-app-static-{account-id}/ --delete
```

#### 6.3 Invalidate CloudFront Cache
```bash
aws cloudfront create-invalidation \
  --distribution-id D111111 \
  --paths "/*"
```

---

## 🛡️ PART 5: SECURITY CHECKLIST

- [ ] HTTPS enabled on all endpoints (CloudFront + ALB)
- [ ] CORS properly configured to allow only frontend domain
- [ ] Database credentials stored in AWS Secrets Manager
- [ ] API rate limiting enabled (currently at 20-30 req/min)
- [ ] SQL injection prevented (Django ORM)
- [ ] CSRF protection enabled
- [ ] XSS protection via Content-Security-Policy headers
- [ ] Dependencies audited for vulnerabilities
- [ ] Logging configured (CloudWatch)
- [ ] Monitoring & alerting setup (CloudWatch alarms)

---

## 📈 PART 6: MONITORING & MAINTENANCE

### CloudWatch Monitoring
- Set up dashboards for:
  - Application response times
  - Error rates & 4xx/5xx responses
  - Database query performance
  - CPU & memory utilization
  
### Alerts
- Error rate > 5%
- Database connection pool exhausted
- Disk space < 10%

### Regular Maintenance
- Review logs weekly
- Update dependencies monthly
- Database backups verified daily
- Cost optimization quarterly

---

## 📋 POST-DEPLOYMENT CHECKLIST

- [ ] Test poll creation end-to-end
- [ ] Verify voting works without duplicates
- [ ] Check real-time updates (2-second polling)
- [ ] Monitor CloudWatch logs for errors
- [ ] Load test with Apache JMeter
- [ ] Document API endpoints in README
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Create runbook for incident response

---

## 🔗 USEFUL COMMANDS

```bash
# View logs
eb logs

# SSH into instance
eb ssh

# Scale application
eb scale 2  # 2 instances

# Monitor health
eb health

# Terminate environment (cleanup)
eb terminate
```

---

## 💰 ESTIMATED MONTHLY COSTS (AWS)

| Service | Tier | Estimate |
|---------|------|----------|
| Elastic Beanstalk (t3.small) | 1 instance | $20/month |
| RDS PostgreSQL (db.t3.micro) | 20GB storage | $25/month |
| S3 Storage | <1GB | <$1/month |
| CloudFront | ~100GB/month | $9/month |
| Data transfer | Standard | ~$5/month |
| **Total** | | **~$60/month** |

---

## 🚨 TROUBLESHOOTING

### Common Issues

**Issue**: 502 Bad Gateway
- Check Elastic Beanstalk logs: `eb logs`
- Verify database connection in environment variables
- Restart instance: `eb appver --verbose`

**Issue**: CORS errors
- Verify CORS_ALLOWED_ORIGINS includes frontend domain
- Check CloudFront headers
- Test with curl: `curl -H "Origin: https://yourdomain.com" -v endpoint`

**Issue**: Database connection timeout
- Check RDS security group allows EB instance
- Verify database is running
- Check connection string format

---

## 📞 NEXT STEPS

1. **Set up AWS account** (if not done)
2. **Create RDS PostgreSQL** instance
3. **Create S3 bucket** for static files
4. **Initialize Elastic Beanstalk** locally
5. **Configure environment variables**
6. **Deploy backend**
7. **Build and upload frontend**
8. **Test end-to-end**
9. **Set up monitoring**
10. **Document API & deployment process**

---

Generated: 2026-03-25
Status: Ready for AWS Deployment

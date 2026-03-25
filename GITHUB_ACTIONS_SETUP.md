# GitHub Actions CI/CD Setup Guide

## 📋 Required GitHub Secrets

To enable the automated CI/CD pipeline, configure the following secrets in your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

### AWS Credentials

#### Option 1: IAM User Credentials (Simpler)
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION=us-east-1
```

#### Option 2: IAM Role (Recommended for Security)
```
AWS_ROLE_ARN=arn:aws:iam::123456789:role/GitHubActionsRole
AWS_REGION=us-east-1
```

### AWS Services

```
AWS_S3_BUCKET_NAME=polling-app-static-{account-id}
AWS_CLOUDFRONT_DISTRIBUTION_ID=D1234567ABC
```

### Optional: Slack Notifications

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## 🔐 Creating AWS IAM User (Option 1 - Simpler)

1. Go to AWS IAM Console
2. Create new user: `github-actions`
3. Attach policies:
   - AmazonElasticBeanstalkFullAccess
   - AmazonS3FullAccess
   - CloudFrontFullAccess
   - CloudWatchLogsFullAccess
4. Generate access keys
5. Add to GitHub secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

---

## 🔐 Creating AWS IAM Role (Option 2 - Recommended)

1. Go to AWS IAM Console → Roles
2. Create role:
   - **Trusted entity**: Web identity
   - **Provider**: token.actions.githubusercontent.com
   - **Audience**: sts.amazonaws.com
3. Attach policies:
   - AmazonElasticBeanstalkFullAccess
   - AmazonS3FullAccess
   - CloudFrontFullAccess
4. Copy **Role ARN**
5. Add to GitHub secrets:
   - `AWS_ROLE_ARN`

**Trust relationship policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

---

## 🔧 GitHub Workflow Customization

Edit `.github/workflows/deploy.yml` to customize:

```yaml
# Environment variables
env:
  AWS_REGION: us-east-1
  EB_ENVIRONMENT: production
  EB_APPLICATION: polling-app

# Deployment branches (change if needed)
on:
  push:
    branches: [main, develop]  # Deploy on push to these branches
```

---

## ✅ Verification

After setting up:

1. Push code to main branch: `git push origin main`
2. Go to GitHub → Actions
3. Monitor workflow execution
4. Check logs for any errors

---

## 📊 Pipeline Stages

1. **test-backend**: Python tests + migrations
2. **test-frontend**: TypeScript + build
3. **security-scan**: Bandit, Safety, pip-audit
4. **deploy**: EB + S3 + CloudFront (only on main)
5. **notify**: Send Slack notification (optional)

---

## 🚨 Troubleshooting

### "Context access might be invalid"
These are YAML linter warnings, not errors. They appear because the linter doesn't recognize GitHub secret variables. The workflow will work fine once you add the secrets.

### Deployment fails
1. Check CloudWatch EB logs: `eb logs`
2. Verify all secrets are configured: Settings → Secrets
3. Verify AWS IAM permissions
4. Check database URL is correct

### Database migration fails
```yaml
# In .github/workflows/deploy.yml, add:
- name: Run migrations
  run: |
    eb ssh
    python manage.py migrate
    exit
```

---

## 📢 Slack Integration

1. Create Slack incoming webhook: https://api.slack.com/messaging/webhooks
2. Copy webhook URL
3. Add to GitHub secrets as `SLACK_WEBHOOK_URL`
4. Workflow will automatically notify on deployment

---

## 🔄 Manual Deployment (without CI/CD)

If you don't want to set up GitHub Actions:

```bash
# Backend
cd backend
eb deploy

# Frontend
cd frontend
npm run build
aws s3 sync dist/ s3://bucket-name/ --delete
aws cloudfront create-invalidation --distribution-id D111111 --paths "/*"
```

---

**Status**: Pipeline configured and ready for deployment automation

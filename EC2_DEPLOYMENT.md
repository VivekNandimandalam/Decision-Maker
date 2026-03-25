# EC2 Deployment Setup Instructions

## ✅ Step 1: Launch EC2 Instance (You're doing this now)
- ✓ Selected: Amazon Linux 2023
- ✓ Instance type: t3.micro
- ✓ Key pair: decision-maker-key
- ✓ Security group: SSH (22), HTTP (80), HTTPS (443) open

After launch, note your **Public IPv4 address** (e.g., `54.123.45.67`)

---

## Step 2: Connect to EC2 and Run Setup Script

Once the EC2 instance is running:

```bash
# SSH into instance (from your computer where you saved decision-maker-key.pem)
ssh -i decision-maker-key.pem ec2-user@YOUR_EC2_IP

# Download setup script
curl -O https://raw.githubusercontent.com/YOUR_USERNAME/Decision-Maker/main/setup-ec2.sh
chmod +x setup-ec2.sh

# Run it (takes ~5 minutes)
./setup-ec2.sh
```

---

## Step 3: Add EC2 Details to GitHub Secrets

After setup completes, go to **GitHub Repo → Settings → Secrets and variables → Actions**

Add these 2 secrets:
- `EC2_HOST`: Your EC2 public IP (e.g., `54.123.45.67`)
- `EC2_SSH_KEY`: Copy the entire content of `decision-maker-key.pem` file

> **How to get the key content:**
> ```bash
> cat decision-maker-key.pem
> ```
> Copy everything including `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----`

---

## Step 4: Push to GitHub to Deploy

```bash
git push origin main
```

This triggers GitHub Actions which will:
- ✓ Run tests
- ✓ Build frontend
- ✓ SSH into your EC2
- ✓ Deploy code
- ✓ Restart services

**Your app is live!** 🚀 Visit: `http://YOUR_EC2_IP/`

---

## Step 5: (Optional) Set Up Custom Domain

If you want a domain instead of IP address:
1. Buy domain (godaddy, namecheap, etc)
2. Point DNS to your EC2 public IP
3. Update nginx config in `/etc/nginx/sites-available/decision-maker`
4. Get SSL with Let's Encrypt (free)

---

## Troubleshooting

### SSH Connection Refused
```bash
# Check security group allows port 22
# Wait ~3 minutes for instance to fully boot
```

### Deployment Fails
```bash
# SSH in and check logs:
ssh -i decision-maker-key.pem ec2-user@YOUR_EC2_IP
sudo journalctl -u gunicorn -n 50
sudo journalctl -u nginx -n 50
```

### See What's Running
```bash
sudo systemctl status gunicorn
sudo systemctl status nginx
```

---

## Cost
- **Free tier**: 750 hours/month of t3.micro
- **No charges** if you stay within free tier
- **Always running**: ~$0/month during free year

---

## Done!
Your app is production-ready and auto-deploys with every push to `main`. 🎉

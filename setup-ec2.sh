#!/bin/bash
set -e

echo "Setting up EC2 server for Decision-Maker..."

# Update system
sudo yum update -y

# Install Python 3.12
sudo yum install -y python3.12 python3.12-pip python3.12-devel

# Install system dependencies
sudo yum install -y git nginx

# Create app directory
mkdir -p /home/ec2-user/Decision-Maker
cd /home/ec2-user/Decision-Maker

# Clone repository (if not already present)
if [ ! -d ".git" ]; then
  git clone https://github.com/YOUR_USERNAME/Decision-Maker.git .
fi

# Setup backend
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create Django migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Deactivate venv
deactivate

# Setup frontend
cd ../frontend
npm install
npm run build

# Configure Nginx
sudo tee /etc/nginx/sites-available/decision-maker > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        alias /home/ec2-user/Decision-Maker/frontend/dist/;
        try_files \$uri \$uri/ /index.html;
        add_header Cache-Control "public, max-age=3600";
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check
    location /health/ {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
EOF

# Enable nginx config
sudo ln -sf /etc/nginx/sites-available/decision-maker /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t

# Create gunicorn systemd service
sudo tee /etc/systemd/system/gunicorn.service > /dev/null <<EOF
[Unit]
Description=Decision-Maker Gunicorn
After=network.target

[Service]
Type=notify
User=ec2-user
WorkingDirectory=/home/ec2-user/Decision-Maker/backend
Environment="PATH=/home/ec2-user/Decision-Maker/backend/venv/bin"
ExecStart=/home/ec2-user/Decision-Maker/backend/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 60 \
    backend.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable nginx
sudo systemctl enable gunicorn
sudo systemctl start nginx
sudo systemctl start gunicorn

echo "✓ Server setup complete!"
echo "Your app is running at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/"

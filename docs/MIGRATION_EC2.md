# AWS EC2 All-in-One Deployment Playbook

This guide details the step-by-step process of migrating the React frontend, FastAPI backend, and local database (SQLite/PostgreSQL) to your newly provisioned AWS EC2 instance.

**Production auth & data are AWS-only:** Admin JWT login (`DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`) and SQLite on the instance. Do not enable Supabase on EC2.

---

## 1. Active Infrastructure Details

The following resources were successfully provisioned in the **ap-south-1** (Mumbai) region:

*   **EC2 Instance ID:** `i-0f8c2fb4d16c2b5a7`
*   **Public IP Address:** `13.232.230.198`
*   **Active VPC ID:** `vpc-0d2dd1e624e5d8847`
*   **Security Group:** `kannans-sg` (`sg-01d18287959e437b3`) — ports 22, 80, and 443 are open.
*   **S3 Backup Bucket:** `kannans-db-backups-987292391022`
*   **SSH Private Key:** [kannans-key-pair.pem](file:///e:/OneDrive/Desktop/Kannans/kannans-key-pair.pem) (saved locally in the project root)

---

## 2. Server Setup & Software Installation

### A. SSH Into Your New EC2 Instance
Run this command from your local terminal inside the project root where `kannans-key-pair.pem` is stored:
```bash
ssh -i "kannans-key-pair.pem" ubuntu@13.232.230.198
```

### B. Update System and Install Core Packages
Once logged into the server, run:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx awscli postgresql postgresql-contrib
```

---

## 3. Clone Repository & Environment Setup

### A. Clone Code
Clone your repository to the `/home/ubuntu` directory:
```bash
git clone https://github.com/chethud/SRIVATSANKA.git /home/ubuntu/srivatsanka
cd /home/ubuntu/srivatsanka/whatsapp
```

### B. Setup Python Environment
Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### C. Create Production `.env`
Create the production environment file inside `/home/ubuntu/srivatsanka/whatsapp/.env`:
```env
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./kannans.db
# OR if using PostgreSQL: DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/postgres

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash

WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-whatsapp-phone-id
WHATSAPP_VERIFY_TOKEN=kannans-verify-token
META_APP_SECRET=your-meta-app-secret
OWNER_PHONE_NUMBER=919945607074

CORS_ORIGINS=https://13.232.230.198,http://13.232.230.198,https://yourdomain.com
DASHBOARD_USERNAME=Admin
DASHBOARD_PASSWORD=Admin@123
JWT_SECRET=your-long-secure-random-jwt-secret
JWT_EXPIRE_HOURS=168

SEED_EXCEL_REFS_ON_STARTUP=false

# Custom variable for backup script
S3_BACKUP_BUCKET=kannans-db-backups-987292391022
```

---

## 4. Run Backend as a Systemd Service

Create a systemd service file `/etc/systemd/system/kannans-backend.service`:
```ini
[Unit]
Description=FastAPI Backend for WhatsApp AI Agent
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/srivatsanka/whatsapp
ExecStart=/home/ubuntu/srivatsanka/whatsapp/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
EnvironmentFile=/home/ubuntu/srivatsanka/whatsapp/.env

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kannans-backend
sudo systemctl start kannans-backend

# Verify the backend status:
sudo systemctl status kannans-backend
```

---

## 5. Build and Configure Nginx (Frontend + Reverse Proxy)

### A. Build the Frontend
In the `website` directory of the project, build the production assets **without Supabase**:
```bash
cd /home/ubuntu/srivatsanka/website
# Ensure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are unset/blank (.env.production does this)
npm install
npm run build
```
This builds static assets to `/home/ubuntu/srivatsanka/website/dist`. Sign-in uses Admin username/password against `/api/auth/login`.

### B. Configure Nginx
Replace `/etc/nginx/sites-available/default` with the following configuration (replace `yourdomain.com` with your domain name if you register one, or leave the IP addresses):

```nginx
server {
    listen 80;
    server_name 13.232.230.198 yourdomain.com www.yourdomain.com;

    # 1. Frontend Static Files
    location / {
        root /home/ubuntu/srivatsanka/website/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 2. Reverse Proxy for API Routes
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded-for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 3. Reverse Proxy for WhatsApp Webhook Routes
    location /webhook {
        proxy_pass http://127.0.0.1:8000/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /dev/ {
        proxy_pass http://127.0.0.1:8000/dev/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Test and restart Nginx:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## 6. Secure Server with Let's Encrypt SSL (Requires Domain Name)

Once you point your custom domain name (e.g. `yourdomain.com`) to `13.232.230.198` in your DNS registrar, run:
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 7. Setup Automated S3 Backups

Configure the [backup-to-s3.sh](file:///e:/OneDrive/Desktop/Kannans/whatsapp/scripts/backup-to-s3.sh) script to back up your database every night.

### A. Set Executable Permissions
```bash
chmod +x /home/ubuntu/srivatsanka/whatsapp/scripts/backup-to-s3.sh
```

### B. Add to Cron Job
Open the system crontab:
```bash
crontab -e
```

Add the following line at the bottom to run the backup every day at 2:00 AM (server time):
```text
0 2 * * * /bin/bash /home/ubuntu/srivatsanka/whatsapp/scripts/backup-to-s3.sh >> /var/log/db_backup.log 2>&1
```

Create the log file:
```bash
sudo touch /var/log/db_backup.log
sudo chown ubuntu:ubuntu /var/log/db_backup.log
```

---

## 8. Verification & Webhook Setup

1.  **Frontend Dashboard:** Navigate to `http://13.232.230.198` in your browser. Verify the dashboard loads successfully.
2.  **API Health:** Visit `http://13.232.230.198/api/health` and verify it returns `{"status":"ok"}`.
3.  **Meta Webhook Configuration:**
    *   Go to [Meta developers portal](https://developers.facebook.com/).
    *   Set the **Webhook URL** to: `http://13.232.230.198/webhook` (or `https://yourdomain.com/webhook` once SSL is active).
    *   Set the **Verify Token** to the same string you put in your `.env` file (`kannans-verify-token`).
4.  **Test Backup:** Run `/home/ubuntu/srivatsanka/whatsapp/scripts/backup-to-s3.sh` manually once on the server, and check the S3 bucket `kannans-db-backups-987292391022` to verify the backup file has successfully uploaded.

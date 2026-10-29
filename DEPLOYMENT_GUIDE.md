# Suraksha Insurance Management System - Production Deployment Guide
**Target Database Engine:** Local Oracle Database 10g Enterprise Edition Release 10.2.0.1.0 (`ORCL` / `SCOTT`)  
**Web Framework:** Python Flask 3.1 + Multi-Threaded Waitress WSGI  
**Platform:** Windows 10/11, Linux, or Docker Container  

---

## 🏛️ System Architecture

```
[ User Browser / Faculty Laptop / Mobile Device ]
                     │  (HTTP / HTTPS Port 5000)
                     ▼
       ┌───────────────────────────────┐
       │   Waitress WSGI Web Server    │
       │   (12 Multi-Threaded Workers) │
       │   Flask Application Tier      │
       │   - RBAC & Session Security   │
       │   - Real-Time DML Execution   │
       │   - Interactive Chart.js Core │
       └──────────────┬────────────────┘
                      │
                      │  (Local REST/HTTP Bridge)
                      ▼
       ┌───────────────────────────────┐
       │  Oracle iSQL*Plus Workspace   │
       │  http://localhost:5560/       │
       └──────────────┬────────────────┘
                      │  (Direct SQLNet Loopback)
                      ▼
       ┌───────────────────────────────┐
       │   Oracle Database 10g R2      │
       │   ORCL SID / Schema: SCOTT    │
       │   14 Tables • 228 Constraints │
       └───────────────────────────────┘
```

---

## 🚀 Deployment Method 1: Windows Intranet & College Lab (Recommended for Viva/Presentations)

This method hosts the portal directly on your machine using the **Waitress Production WSGI Server** and allows anyone connected to the same Wi-Fi / LAN router (faculty, classmates, external evaluators) to open the portal from their own laptops or mobile phones.

### Step 1: Install Dependencies
Open PowerShell or Command Prompt in the project folder and run:
```powershell
pip install -r requirements.txt
```

### Step 2: One-Click Launch
Double-click `start_production.bat`  
*OR* run via PowerShell:
```powershell
python deploy_production.py
```

### Step 3: Accessing the Portal
The console will print both URLs:
- **Local Access (Your Laptop):** `http://127.0.0.1:5000` or `http://localhost:5000`
- **Intranet / Mobile Access (Same Wi-Fi):** `http://<YOUR_IP_ADDRESS>:5000`  
  *(Example: `http://192.168.1.45:5000`)*

### Step 4: Allow Port 5000 in Windows Firewall (One-Time)
If classmates or faculty cannot connect over Wi-Fi, run this in an Administrator PowerShell to allow inbound traffic on port 5000:
```powershell
New-NetFirewallRule -DisplayName "Suraksha Insurance App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

---

## 🌐 Deployment Method 2: Public HTTPS Remote Access via Cloudflare Tunnel (Zero Port-Forwarding)

If your teacher or evaluator is remote (not on the same Wi-Fi) and needs a live public link, use a free secure tunnel. No router configuration or static IP needed!

### Option A: Using Free Cloudflare Tunnel (No Account Required)
1. Download `cloudflared.exe` from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases).
2. With the server running, open a new terminal and run:
   ```powershell
   cloudflared tunnel --url http://localhost:5000
   ```
3. Cloudflare will output an instant public HTTPS link (e.g., `https://random-words.trycloudflare.com`). Anyone in the world can open this link in their browser!

### Option B: Using Localtunnel (Requires Node.js)
```bash
npx localtunnel --port 5000
```

---

## 🐳 Deployment Method 3: Containerized Deployment (Docker Compose)

For cloud virtual machines (AWS EC2, DigitalOcean, Azure VM, Ubuntu Server):

1. **Build and Run Containers:**
   ```bash
   docker compose up --build -d
   ```
2. **Check Container Status:**
   ```bash
   docker compose ps
   ```
3. **View Live Application Logs:**
   ```bash
   docker compose logs -f
   ```
4. **Shut Down:**
   ```bash
   docker compose down
   ```

---

## 🔐 Authorized Personnel & RBAC Security Reference

The system enforces strict role-based access control. Unauthenticated requests are intercepted and redirected to `/login`.

| Role Identifier | Username | Password | Department | Permissions & Access Scope |
| :--- | :--- | :--- | :--- | :--- |
| **System Administrator** | `admin` | `admin123` | Executive Underwriting | Full Root Access, User Provisioning, Underwriting, Claim Settlements, DML Deletions |
| **Lead Underwriter** | `underwriter` | `policy123` | Actuarial & Risk | Policy Underwriting, Contract Lifecycle, Risk Portfolio |
| **Claims Surveyor** | `surveyor` | `claims123` | Claims Adjudication | Claim Inspection, 1-Click Approvals, Rejections, Loss Assessments |
| **Agency Manager** | `agent` | `agent123` | Branch Distribution | Policyholder Onboarding, Policy Issuance, Premium Collections |
| **Oracle DBA** | `scott` | `tiger` | Database Systems | Direct Oracle 10g Schema Administration, SQL Console, Health Metrics |

### Adding New Authorized Users
Log in as `admin`, navigate to **Authorized Personnel** (`/users`), and click **`+ Authorize New User`**. Fill in the personnel details and assign their security clearance level.

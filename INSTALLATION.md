# AIOps Sentinel — Zero-to-Hero Installation Guide

> **Audience:** Anyone with a fresh operating system (Windows 10/11, Ubuntu/Debian Linux, or macOS).  
> **Prerequisites Assumed:** None. This guide begins from downloading Git and Python.

---

## Table of Contents
1. [System Requirements](#1-system-requirements)
2. [Windows Setup from Zero](#2-windows-setup-from-zero)
   - [Step 2.1: Install Git & Git Bash](#step-21-install-git--git-bash)
   - [Step 2.2: Install Python 3.11 or 3.13](#step-22-install-python-311-or-313)
   - [Step 2.3: Install Node.js & npm (LTS v20+)](#step-23-install-nodejs--npm-lts-v20)
   - [Step 2.4: Install Docker Desktop & WSL 2](#step-24-install-docker-desktop--wsl-2)
   - [Step 2.5: Configure PowerShell Execution Policy](#step-25-configure-powershell-execution-policy)
3. [Linux / macOS Setup](#3-linux--macos-setup)
4. [Cloning the Repository](#4-cloning-the-repository)
5. [Automated One-Click Setup](#5-automated-one-click-setup)
6. [Manual Step-by-Step Installation (Fallback)](#6-manual-step-by-step-installation-fallback)
   - [Step 6.1: Initialize Environment Files](#step-61-initialize-environment-files)
   - [Step 6.2: Configure Python Virtual Environment](#step-62-configure-python-virtual-environment)
   - [Step 6.3: Generate Prisma ORM Client](#step-63-generate-prisma-orm-client)
   - [Step 6.4: Install Frontend Dependencies](#step-64-install-frontend-dependencies)
   - [Step 6.5: Launch Docker Microservices](#step-65-launch-docker-microservices)
   - [Step 6.6: Synchronize Database Schema](#step-66-synchronize-database-schema)
   - [Step 6.7: Launch Windows Telemetry Agent](#step-67-launch-windows-telemetry-agent)
7. [System Verification & Health Checks](#7-system-verification--health-checks)
8. [Next Steps](#8-next-steps)

---

## 1. System Requirements

| Hardware / Resource | Minimum Recommended | Optimal Production / Benchmark |
| :--- | :--- | :--- |
| **Processor** | 4-Core x86_64 CPU (Intel i5 8th gen+ or AMD Ryzen 3000+) | 8-Core Intel Core i7 / AMD Ryzen 7+ |
| **RAM** | 8 GB RAM (minimum for Docker + DB) | 16 GB+ RAM (comfortable for all 12 containers + ML models) |
| **Disk Space** | 10 GB free SSD storage | 25 GB free SSD storage |
| **Operating System** | Windows 10/11 64-bit (Build 19041+), Ubuntu 22.04 LTS, or macOS 12+ | Windows 11 Pro 64-bit with WSL 2 |

---

## 2. Windows Setup from Zero

Follow these steps sequentially on a fresh Windows laptop.

### Step 2.1: Install Git & Git Bash
1. Download the official installer from [git-scm.com/download/win](https://git-scm.com/download/win).
2. Run the `.exe` installer.
3. During setup:
   - Keep default editor options.
   - Choose *"Git from the command line and also from 3rd-party software"*.
   - Ensure *"Checkout Windows-style, commit Unix-style line endings"* is selected.
4. Verify in PowerShell:
   ```powershell
   git --version
   # Expected output: git version 2.4x.x.windows.1
   ```

### Step 2.2: Install Python 3.11 or 3.13
1. Download Python from [python.org/downloads/windows](https://www.python.org/downloads/windows/).
2. **CRITICAL STEP:** On the very first screen of the installer, check the box:
   - **`[x] Add python.exe to PATH`**
3. Select *"Customize installation"*, ensure `pip` and `tcl/tk` are checked, and click *"Install"*.
4. On the final screen, click *"Disable path length limit"*.
5. Verify in a fresh PowerShell window:
   ```powershell
   python --version
   # Expected: Python 3.11.x or Python 3.13.x
   pip --version
   ```

### Step 2.3: Install Node.js & npm (LTS v20+)
1. Download the LTS installer from [nodejs.org](https://nodejs.org/).
2. Run the `.msi` setup wizard with standard defaults.
3. Verify in PowerShell:
   ```powershell
   node --version
   # Expected: v20.x.x or v22.x.x
   npm --version
   # Expected: 10.x.x
   ```

### Step 2.4: Install Docker Desktop & WSL 2
1. Open PowerShell **as Administrator** and enable the Windows Subsystem for Linux (WSL 2):
   ```powershell
   wsl --install
   ```
   *Note: If prompted, reboot your computer to complete WSL initialization.*
2. Download Docker Desktop from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/).
3. Run the installer and ensure *"Use WSL 2 instead of Hyper-V (recommended)"* is checked.
4. Launch Docker Desktop and accept the service agreement.
5. In Docker Desktop Settings (`Settings` -> `General`), ensure *"Use the WSL 2 based engine"* is enabled.
6. Verify in PowerShell:
   ```powershell
   docker --version
   docker compose version
   # Expected: Docker Compose version v2.x.x
   ```

### Step 2.5: Configure PowerShell Execution Policy
Windows restricts unsigned script execution by default. To allow `setup.ps1` and `run.ps1` to execute:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

---

## 3. Linux / macOS Setup

On Ubuntu / Debian:
```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip nodejs npm curl
# Install Docker: https://docs.docker.com/engine/install/ubuntu/
sudo usermod -aG docker $USER
```

On macOS (using Homebrew):
```bash
brew install git python node docker docker-compose
```

---

## 4. Cloning the Repository

Open PowerShell or Terminal and navigate to your preferred development folder:
```powershell
cd C:\Users\YourUsername\Projects
git clone https://github.com/your-username/MLOPS_CP.git
cd MLOPS_CP
```

---

## 5. Automated One-Click Setup

The repository includes a turnkey setup script that handles all dependency installations, environment configuration, database bootstrapping, and container orchestration automatically:

```powershell
# On Windows:
.\setup.ps1

# On Linux / macOS / WSL:
chmod +x setup.sh healthcheck.sh run.sh stop.sh
./setup.sh
```

**What the setup script performs automatically:**
1. Validates Python, Node.js, and Docker runtimes.
2. Creates `.env`, `backend/.env`, and `aiops-sentinel/.env` from templates.
3. Provisions a dedicated Python virtual environment in `backend/.venv`.
4. Installs FastAPI, PyTorch, LightGBM, scikit-learn, HDBSCAN, and Prisma.
5. Generates the type-safe Prisma database client.
6. Compiles the React/TypeScript frontend.
7. Starts all 12 Docker microservices (`docker compose up -d`).
8. Pushes database schemas and seeds default administrative credentials.
9. Runs a comprehensive health audit across all containers and REST routes.

---

## 6. Manual Step-by-Step Installation (Fallback)

If you prefer to understand each moving piece or execute manual setup, follow these steps:

### Step 6.1: Initialize Environment Files
```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item aiops-sentinel/.env.example aiops-sentinel/.env
```

### Step 6.2: Configure Python Virtual Environment
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r ../windows-agent-requirements.txt
```

### Step 6.3: Generate Prisma ORM Client
With the virtual environment activated in `backend`:
```powershell
python -m prisma generate
```

### Step 6.4: Install Frontend Dependencies
In a separate terminal or navigating back:
```powershell
cd ../aiops-sentinel
npm install --legacy-peer-deps
npm run build
cd ..
```

### Step 6.5: Launch Docker Microservices
```powershell
docker compose up -d
```
Verify all 12 containers are running:
```powershell
docker compose ps
```

### Step 6.6: Synchronize Database Schema
```powershell
cd backend
npx prisma db push --accept-data-loss
cd ..
```

### Step 6.7: Launch Windows Telemetry Agent
```powershell
& backend\.venv\Scripts\python.exe windows_agent.py
```

---

## 7. System Verification & Health Checks

Run the automated health checker to verify all 24 system components (12 containers, 11 REST endpoints, and host daemon):

```powershell
.\healthcheck.ps1
```

**Expected Healthy Terminal Output:**
```text
==========================================================================
AIOPS SENTINEL SYSTEM HEALTH CHECK & AUDIT
==========================================================================

Health Audit Summary Table:

Component                 Target                                            Status Latency Details                     
---------                 ------                                            ------ ------- -------                     
mlops_cp-backend-1        Docker Container                                  PASS   -       Running: True | Health: healthy
mlops_cp-frontend-1       Docker Container                                  PASS   -       Running: True | Health: unmonitored
mlops_cp-nginx-1          Docker Container                                  PASS   -       Running: True | Health: unmonitored
mlops_cp-db-1             Docker Container                                  PASS   -       Running: True | Health: healthy
mlops_cp-redis-1          Docker Container                                  PASS   -       Running: True | Health: healthy
mlops_cp-prometheus-1     Docker Container                                  PASS   -       Running: True | Health: unmonitored
mlops_cp-grafana-1        Docker Container                                  PASS   -       Running: True | Health: unmonitored
mlops_cp-loki-1           Docker Container                                  PASS   -       Running: True | Health: unmonitored
mlops_cp-otel-collector-1 Docker Container                                  PASS   -       Running: True | Health: unmonitored
mlops_cp-cadvisor-1       Docker Container                                  PASS   -       Running: True | Health: healthy
mlops_cp-node-exporter-1  Docker Container                                  PASS   -       Running: True | Health: unmonitored
mlops_cp-promtail-1       Docker Container                                  PASS   -       Running: True | Health: unmonitored
FastAPI Health Probe      http://localhost:8000/api/v1/health               PASS   45ms    HTTP 200 (Protected)        
Auth Status Probe         http://localhost:8000/api/v1/auth/status          PASS   34ms    HTTP 200 (Protected)        
Prometheus ASGI Metrics   http://localhost:8000/internal/metrics            PASS   66ms    HTTP 200 (Protected)        
ML Anomaly Engine         http://localhost:8000/api/v1/ml/anomaly/health    PASS   34ms    HTTP 200 (Protected)        
ML HDBSCAN Clusterer      http://localhost:8000/api/v1/ml/cluster/health    PASS   29ms    HTTP 200 (Protected)        
ML GraphSAGE RCA GNN      http://localhost:8000/api/v1/ml/root-cause/health PASS   48ms    HTTP 200 (Protected)        
ML LightGBM Risk Engine   http://localhost:8000/api/v1/ml/risk/health       PASS   36ms    HTTP 200 (Protected)        
Nginx Web Ingress         http://localhost:8081                             PASS   67ms    HTTP 200 (Protected)        
Prometheus UI             http://localhost:9090/-/healthy                   PASS   24ms    HTTP 200 (Protected)        
Grafana Dashboard         http://localhost:3000/api/health                  PASS   25ms    HTTP 200 (Protected)        
Loki Ingestion Status     http://localhost:3100/ready                       PASS   24ms    HTTP 200 (Protected)        
Windows Telemetry Agent   Local OS Daemon                                   PASS   -       Active (PID: 20456)         

Result: 24/24 Components Operating Normally.
```

---

## 8. Next Steps
- Open the web dashboard: [http://localhost:8081](http://localhost:8081)
- Explore interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Read the [Architecture Guide](file:///c:/Users/Ifreen/Downloads/MLOPS_CP/ARCHITECTURE.md) and [ML Models Documentation](file:///c:/Users/Ifreen/Downloads/MLOPS_CP/ML_MODELS.md).
- To stop the system safely without losing database records, run:
  ```powershell
  .\stop.ps1
  ```

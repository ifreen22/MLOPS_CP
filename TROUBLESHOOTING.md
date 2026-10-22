# AIOps Sentinel — Troubleshooting & Diagnostic Guide

This guide provides targeted solutions for common installation, execution, networking, and runtime errors encountered across the platform.

---

## 1. Quick Diagnostic Checklist

If experiencing unexpected behavior, run the automated health check first:
```powershell
.\healthcheck.ps1
```
This inspects all 12 containers, checks API response codes, and verifies the Windows agent daemon.

---

## 2. Common Errors & Resolution Matrix

### Issue 2.1: Port Conflict (Port 8000, 8081, 5432, 9090, or 3000 in use)
- **Symptom:** Docker fails to start with `Bind for 0.0.0.0:8000 failed: port is already allocated`.
- **Root Cause:** Another local service (e.g., another PostgreSQL instance, local Grafana, or leftover Node process) is holding the port.
- **Resolution:**
  1. Identify the offending process in PowerShell:
     ```powershell
     netstat -ano | findstr :8000
     ```
  2. The last column is the process ID (PID). Inspect the process:
     ```powershell
     Get-Process -Id <PID>
     ```
  3. Terminate the conflict:
     ```powershell
     Stop-Process -Id <PID> -Force
     ```
  4. Or edit `docker-compose.yml` to remap host ports (e.g., change `"8000:8000"` to `"8005:8000"`).

---

### Issue 2.2: PowerShell Script Execution Restricted
- **Symptom:** Running `.\setup.ps1` produces:
  `File ... cannot be loaded because running scripts is disabled on this system.`
- **Root Cause:** Windows default execution policy restricts unsigned PowerShell scripts.
- **Resolution:**
  Open PowerShell and run:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  ```

---

### Issue 2.3: Docker Daemon Not Running / WSL 2 Errors
- **Symptom:** `error during connect: This error may indicate that the docker daemon is not running`.
- **Root Cause:** Docker Desktop has not finished booting, or WSL 2 backend integration is disabled.
- **Resolution:**
  1. Launch **Docker Desktop** from the Windows Start menu.
  2. Wait until the whale icon in the taskbar turns solid green.
  3. If WSL 2 throws an error, update WSL in PowerShell (Admin):
     ```powershell
     wsl --update
     wsl --shutdown
     ```
  4. Restart Docker Desktop.

---

### Issue 2.4: Prisma Client Out-of-Sync (`prisma: not found` or query errors)
- **Symptom:** Backend logs report `PrismaClientInitializationError: Could not find Prisma Query Engine`.
- **Root Cause:** Prisma client was not generated inside the active Python virtual environment.
- **Resolution:**
  ```powershell
  cd backend
  & .\.venv\Scripts\python.exe -m prisma generate
  npx prisma db push --accept-data-loss
  cd ..
  ```

---

### Issue 2.5: Windows Telemetry Agent Returns HTTP 401 Unauthorized
- **Symptom:** `windows_agent.py` logs:
  `[ERROR] Failed to send telemetry: HTTP 401 Unauthorized`.
- **Root Cause:** The `AGENT_API_TOKEN` configured in your root `.env` or `backend/.env` does not match the token passed by `windows_agent.py`.
- **Resolution:**
  1. Verify the token in `.env`:
     ```text
     AGENT_API_TOKEN=x3Rxw2keZYcsthfajgRG7Y1OmopSfD6zrfNfB5VfDtg
     ```
  2. Ensure `windows_agent.py` references the same token. Restart the agent:
     ```powershell
     Stop-Process -Name python -ErrorAction SilentlyContinue
     & backend\.venv\Scripts\python.exe windows_agent.py
     ```

---

### Issue 2.6: PyTorch or LightGBM C++ DLL Missing on Windows
- **Symptom:** `ImportError: DLL load failed while importing _lightgbm: The specified module could not be found.`
- **Root Cause:** Windows lacks the Microsoft Visual C++ Redistributable runtime.
- **Resolution:**
  Download and install the official Microsoft Visual C++ Redistributable package:
  [Visual C++ 2015-2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe).

---

### Issue 2.7: Playwright Tests Failing on Browser Launch
- **Symptom:** `browserType.launch: Executable doesn't exist at C:\Users\...\AppData\Local\ms-playwright`.
- **Root Cause:** Playwright browser binaries have not been downloaded.
- **Resolution:**
  ```powershell
  cd aiops-sentinel
  npx playwright install --with-deps chromium
  npm run test:e2e
  ```

---

## 3. Log Inspection Commands

To view real-time logs from any running container:
```powershell
# Backend API logs
docker compose logs -f backend

# Database logs
docker compose logs -f db

# Ingress Proxy logs
docker compose logs -f nginx

# Prometheus scraper logs
docker compose logs -f prometheus
```

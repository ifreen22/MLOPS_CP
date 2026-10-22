# Final Real Telemetry Integration Report

## 1. Objective Achieved
AIOps Sentinel now monitors the **real machine** it is running on. All simulated telemetry, random JSON data, and hardcoded `Math.random()` endpoints have been completely replaced with genuine hardware and process-level metrics sourced from the host operating system.

## 2. Telemetry Flow Architecture
The data flows seamlessly from the raw OS to the end user:
1. **Windows Host**: Operating system (CPU cores, RAM buffers, physical disk partitions, running executable tasks).
2. **Backend (FastAPI)**: A background asynchronous thread (`app.main`) loops every 5 seconds, invoking the `TelemetryService` (which uses `psutil`) to capture deep process metrics.
3. **Database (PostgreSQL via Prisma)**: Hardware trends are persisted historically in the `HostTelemetry` and `HostProcess` tables.
4. **AI Orchestrator (ML Pipeline)**: The `/api/v1/ml/analyze` endpoint intercepts real processes (e.g. `chrome.exe`, `code.exe`). If Chrome is consuming > 20% CPU, the orchestrator generates a contextualized AI Recommendation block dynamically.
5. **Frontend (Dashboard.tsx)**: React connects to `/api/v1/system/live` to render true Process IDs (PIDs), accurate memory percentages, and real network I/O. 

## 3. Fake Metrics Removed
- **Frontend Dashboard**: Removed `mockIncidents` array. Replaced hardcoded "Deploy: cart-v3" and "Scale Up Frontend" static AI Action Radar blocks with dynamically iterated `recommendations`.
- **Frontend State**: Erased `Math.random()` simulation loops inside `useSystemTelemetry.ts`.
- **Backend AI Engine**: Replaced dummy standard topological values in `ml_orchestrator_controller.py` with actual deployment sizes (process count) and live memory loads, deriving contextually relevant AI action items instead of generic text.

## 4. Components & Collectors Added

### Backend
- **Libraries Added:** `psutil` (Cross-platform system hardware API) and `wmi` (Windows Management Instrumentation).
- **Database Schema Updated:** Created models `HostTelemetry` (cpu, memory, disk, network) and `HostProcess` (pid, name, load).
- **`app/services/telemetry_service.py`**: A robust OS scanner fetching top 24 active process metrics, physical core counts, clock speeds, and swap utilization.
- **`app/api/v1/controllers/system_controller.py`**: Exposes `/api/v1/system/live` and `/api/v1/system/history` to the frontend.

### Frontend
- **Mission Control (`Dashboard.tsx`)**: Rebuilt from scratch using Framer Motion and Recharts to map actual running processes to a visual node-topology heatmap. If a node is shown, hovering it reveals the specific real-world executable name (e.g., `docker`, `python`) and its exact load on the machine.

### Windows Native Support
- **`start_windows.bat`**: A native startup script was created at the repository root. Docker containers run in isolated Linux VMs and cannot "see" native Windows processes like Chrome or VS Code. Running the script natively starts the Python Uvicorn server directly on Windows, allowing `psutil` to achieve total system process visibility and accurately capture native telemetry.

# System Data Flow

The flow of data spans from low-level OS calls up to the React frontend UI in an asynchronous pipeline.

1. **Native OS (Windows)**
   - `psutil` queries CPU cores, virtual memory, disks, and active process PIDs (Chrome, VS Code, etc.).
   - `GPUtil` queries NVIDIA/AMD GPU metrics.
   - `wmi` is available for deep Windows Management Instrumentation if required.

2. **Windows Agent (`windows_agent.py`)**
   - Polls `/api/v1/system/settings` to determine if "Start Monitoring" was pressed.
   - If active, collects telemetry and POSTs to `/api/v1/system/telemetry`.
   
3. **FastAPI Backend (Receiver & ML Engine)**
   - Receives POST payload.
   - Stores telemetry in `HostTelemetry` and `HostProcess` Postgres tables via Prisma.
   - Caches the latest packet in a global `last_telemetry` variable.

4. **React Frontend (`useSystemTelemetry.ts`)**
   - Uses `axios` to poll `/api/v1/system/live` at the configured interval.
   - Triggers a concurrent POST to `/api/v1/ml/analyze` to evaluate the current packet.
   
5. **AI Orchestrator**
   - Receives the latest packet.
   - Detects the highest CPU-consuming PID (e.g. `chrome.exe`).
   - Appends contextual remediation strings ("Close Chrome tabs to free up CPU").
   
6. **Dashboard (`Dashboard.tsx`)**
   - React processes the final packet and orchestrator recommendations, driving the Recharts UI and Top 24 Process Heatmap completely dynamically.

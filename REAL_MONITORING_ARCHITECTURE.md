# Real Monitoring Architecture

AIOps Sentinel completely eschews simulated data, relying entirely on genuine, native Windows process and hardware metrics.

## Key Principles
1. **Zero Mocking:** No `Math.random()`, no static JSON, and no placeholder metrics. Every percentage points back to a real system call.
2. **Opt-In Telemetry:** The platform remains completely dormant (Idle state) until a user explicitly clicks "Start Monitoring" in the Mission Control dashboard. 
3. **Docker Awareness:** When the backend detects it is running within an isolated Docker Linux VM, it warns the user that host telemetry is unavailable, directing them to the native Windows Agent.

## Backend Receivers (Not Pollers)
The FastAPI backend acts purely as a receiver and ML Orchestrator. It exposes:
- `POST /api/v1/system/telemetry`: The ingestion endpoint where the native agent submits metrics.
- `GET /api/v1/system/settings`: Returns polling intervals and monitoring state (Idle vs Monitoring).
- `GET /api/v1/system/live`: The frontend hook reads the latest telemetry from this cache directly.

By moving polling out of the backend and into the native OS, we bypass containerization limitations entirely.

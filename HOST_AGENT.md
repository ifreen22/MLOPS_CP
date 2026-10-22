# Windows Host Agent (`windows_agent.py`)

Due to Docker running within a Hyper-V/WSL2 Linux VM on Windows, backend APIs running inside `mlops_cp-backend` cannot see the native Windows process tree (e.g., they only see Linux Docker processes).

To satisfy the requirement of genuine machine monitoring, the `windows_agent.py` was created.

## Responsibilities
1. **Settings Sync**: Connects to the backend to check if the user has opted in (`isMonitoring == True`). 
2. **Deep Telemetry**: 
   - CPU (Logical/Physical Cores, frequencies, % per process).
   - RAM (Total, Used, Available).
   - Network I/O (Bytes sent/recv).
   - GPU (Using GPUtil to fetch temp, load, memory).
3. **Transmission**: Flattens the system information into a nested JSON payload and POSTs it directly to the backend database.
4. **Action Execution**: When Auto Recovery is enabled, the agent will poll `/api/v1/system/actions`, read pending commands (e.g. `TERMINATE_PROCESS PID`), execute them via OS-level APIs (e.g. `os.kill`), and report the `SUCCESS` or `FAILED` status back.

## Usage
Simply run:
`python windows_agent.py`
on your local host machine to begin streaming native Windows telemetry to the Dockerized AIOps Sentinel platform.

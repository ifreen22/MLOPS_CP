# Auto Recovery Engine

AIOps Sentinel features a closed-loop "Auto Recovery" engine capable of acting on ML Orchestrator insights.

## Safety & Opt-In
By default, the platform is restricted to Stage 1 (Detect) and Stage 2 (Recommend). It will **never** execute destructive actions without explicit permission.

To reach Stage 3 (Auto Execute), the user must check the **"Auto Recovery"** checkbox in the Mission Control header.

## Workflow
1. **Anomaly Detection**: `ml_orchestrator_controller.py` evaluates the latest telemetry packet and isolates the highest-load PIDs.
2. **Action Queue Generation**: If Auto Recovery is enabled and a process exceeds safe thresholds (e.g., > 20% CPU for Chrome, Docker, Code), the backend inserts a `TERMINATE_PROCESS` command into the Postgres `ActionQueue` table.
3. **Agent Polling**: The native `windows_agent.py` pulls from `/api/v1/system/actions`.
4. **Execution**: The Agent executes `os.kill(pid, 9)` to forcefully terminate the runaway process, freeing up system resources automatically.
5. **Callback**: The Agent hits the `{action_id}/complete` webhook to mark the action as `SUCCESS` or `FAILED`.

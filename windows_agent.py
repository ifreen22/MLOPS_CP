import psutil
import requests
import time
import socket
import os
import shutil
import subprocess
import platform
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    import wmi
except ImportError:
    wmi = None

try:
    import GPUtil
except ImportError:
    GPUtil = None

BACKEND_URL = os.environ.get(
    "AIOPS_SYSTEM_API_URL",
    "http://127.0.0.1:8000/api/v1/system"
).rstrip("/")
AGENT_API_TOKEN = os.environ.get("AGENT_API_TOKEN", "")
AGENT_HEADERS = {"X-Agent-Token": AGENT_API_TOKEN}
_last_net_io = psutil.net_io_counters()
_last_net_time = time.monotonic()


def _raise_for_agent_response(response):
    if response.status_code == 401:
        raise requests.HTTPError(
            "Agent authentication failed. Verify AGENT_API_TOKEN matches the "
            "backend and use the agent endpoint under "
            "/api/v1/system/agent/settings, not /api/v1/system.",
            response=response,
        )
    response.raise_for_status()


def get_telemetry():
    global _last_net_io, _last_net_time
    cpu_percent = psutil.cpu_percent(interval=0.1)
    net_io = psutil.net_io_counters()
    now = time.monotonic()
    elapsed = max(now - _last_net_time, 0.001)
    upload_speed = max(net_io.bytes_sent - _last_net_io.bytes_sent, 0) / elapsed
    download_speed = max(net_io.bytes_recv - _last_net_io.bytes_recv, 0) / elapsed
    _last_net_io = net_io
    _last_net_time = now

    drives = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = shutil.disk_usage(partition.mountpoint)
            percent = (usage.used / usage.total * 100) if usage.total else 0
            drives.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": percent,
            })
        except Exception:
            continue
    disk_total = sum(drive["total"] for drive in drives)
    disk_used = sum(drive["used"] for drive in drives)

    telemetry = {
        "cpu": {
            "usage_percent": cpu_percent,
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "current_freq": psutil.cpu_freq().current if hasattr(psutil, "cpu_freq") and psutil.cpu_freq() else 0,
            "max_freq": psutil.cpu_freq().max if hasattr(psutil, "cpu_freq") and psutil.cpu_freq() else 0,
            "load_avg": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [0,0,0],
        },
        "ram": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "used": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "drives": drives,
            "total": disk_total,
            "used": disk_used,
            "percent": (disk_used / disk_total * 100) if disk_total else 0,
        },
        "network": {
            "upload_speed": upload_speed,
            "download_speed": download_speed,
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
        },
        "battery_percent": None,
        "temperature": None,
        "gpu": None,
        "processes": [],
        "system": {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "uptime": time.time() - psutil.boot_time()
        },
        "timestamp": datetime.now().astimezone().isoformat(),
    }

    # Battery
    if hasattr(psutil, "sensors_battery"):
        battery = psutil.sensors_battery()
        if battery:
            telemetry["battery_percent"] = battery.percent

    # GPU
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                telemetry["gpu"] = {
                    "name": gpus[0].name,
                    "load": gpus[0].load * 100,
                    "temperature": gpus[0].temperature,
                    "memory_total": gpus[0].memoryTotal,
                    "memory_used": gpus[0].memoryUsed
                }
        except Exception:
            pass

    # Temperatures
    if hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures()
            if temps and list(temps.values()):
                telemetry["temperature"] = list(temps.values())[0][0].current
        except Exception:
            pass

    # Top processes
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'exe', 'create_time']):
        try:
            p.info['cpu_percent'] = p.cpu_percent()
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Sort by CPU
    procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
    telemetry["processes"] = procs[:24]

    return telemetry

def main():
    if not AGENT_API_TOKEN:
        raise RuntimeError("Set AGENT_API_TOKEN in the project .env file.")

    print("Starting Windows Telemetry Agent...")
    while True:
        try:
            # Fetch settings
            settings_res = requests.get(
                f"{BACKEND_URL}/agent/settings",
                headers=AGENT_HEADERS,
                timeout=5,
            )
            _raise_for_agent_response(settings_res)
            if settings_res.status_code == 200:
                settings = settings_res.json()
                is_monitoring = settings.get("isMonitoring", False)
                polling_interval = settings.get("pollingInterval", 2)
                auto_recovery = settings.get("autoRecovery", False)

                if is_monitoring:
                    # Collect and send
                    data = get_telemetry()
                    telemetry_res = requests.post(
                        f"{BACKEND_URL}/telemetry",
                        json=data,
                        headers=AGENT_HEADERS,
                        timeout=10,
                    )
                    _raise_for_agent_response(telemetry_res)

                    # Action queue
                    actions_res = requests.get(
                        f"{BACKEND_URL}/actions",
                        headers=AGENT_HEADERS,
                        timeout=5,
                    )
                    _raise_for_agent_response(actions_res)
                    if actions_res.status_code == 200:
                        actions = actions_res.json()
                        for action in actions:
                            action_id = action.get("id")
                            action_type = action.get("actionType")
                            target = action.get("target")
                            status = "SUCCESS"
                            result_detail = "Action completed."
                            
                            try:
                                if action_type == "TERMINATE_PROCESS":
                                    if not auto_recovery:
                                        raise ValueError("Auto Recovery is disabled.")
                                    pid = int(target)
                                    if pid <= 4 or pid == os.getpid():
                                        raise ValueError("Refusing to terminate a protected process.")
                                    observed = next(
                                        (item for item in data["processes"] if item.get("pid") == pid),
                                        None,
                                    )
                                    if not observed or float(observed.get("cpu_percent", 0) or 0) < 20:
                                        raise ValueError("Process is no longer eligible based on the latest telemetry sample.")
                                    expected_name = str(action.get("processName") or "").strip().lower()
                                    expected_create_time = action.get("processCreateTime")
                                    if not expected_name or expected_create_time is None:
                                        raise ValueError("The queued action has no verified process identity.")
                                    observed_name = str(observed.get("name") or "").strip().lower()
                                    observed_create_time = observed.get("create_time")
                                    if observed_name != expected_name or observed_create_time is None:
                                        raise ValueError("The process identity no longer matches the queued action.")

                                    process = psutil.Process(pid)
                                    process_name = process.name().lower()
                                    actual_create_time = process.create_time()
                                    if process_name != expected_name or abs(
                                        actual_create_time - float(expected_create_time)
                                    ) > 0.01 or abs(
                                        float(observed_create_time) - float(expected_create_time)
                                    ) > 0.01:
                                        raise ValueError("The PID now refers to a different process; refusing termination.")
                                    protected_processes = {
                                        "system", "registry", "smss.exe", "csrss.exe",
                                        "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe",
                                    }
                                    if process_name in protected_processes:
                                        raise ValueError(f"Refusing to terminate protected process {process_name}.")
                                    process.terminate()
                                    process.wait(timeout=5)
                                    print(f"Terminated process {pid} ({process_name})")
                                    result_detail = f"Terminated {process_name} (PID {pid})."
                                else:
                                    raise ValueError(f"Unsupported action type: {action_type}")
                            except Exception as e:
                                status = "FAILED"
                                result_detail = f"{type(e).__name__}: {e}"[:2000]
                                print(f"Failed action {action_type}: {e}")

                            completion_res = requests.post(
                                f"{BACKEND_URL}/actions/{action_id}/complete",
                                json={"status": status, "result": result_detail},
                                headers=AGENT_HEADERS,
                                timeout=5,
                            )
                            _raise_for_agent_response(completion_res)
                
                time.sleep(polling_interval)
            else:
                time.sleep(2)
        except Exception as e:
            print(f"Agent Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()

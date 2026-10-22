import psutil
import platform
import socket
import os
from datetime import datetime
import asyncio
from prisma import Prisma
try:
    import wmi
except ImportError:
    wmi = None

class TelemetryService:
    def __init__(self, db: Prisma):
        self.db = db
        # Initialize network counters
        self.net_io_start = psutil.net_io_counters()
        self.last_net_time = datetime.now()

    def get_live_telemetry(self):
        # CPU
        cpu_usage = psutil.cpu_percent(interval=None)
        cpu_logical = psutil.cpu_count(logical=True)
        cpu_physical = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()
        
        try:
            load_avg = psutil.getloadavg()
        except Exception:
            load_avg = [0.0, 0.0, 0.0]

        # RAM
        mem = psutil.virtual_memory()

        # Disk
        disks = []
        total_disk = 0
        used_disk = 0
        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt' and 'cdrom' in part.opts or part.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_disk += usage.total
                used_disk += usage.used
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except Exception:
                pass

        # Network
        now = datetime.now()
        net_io = psutil.net_io_counters()
        time_diff = (now - self.last_net_time).total_seconds()
        
        if time_diff > 0:
            upload_speed = (net_io.bytes_sent - self.net_io_start.bytes_sent) / time_diff
            download_speed = (net_io.bytes_recv - self.net_io_start.bytes_recv) / time_diff
        else:
            upload_speed = 0
            download_speed = 0
            
        self.net_io_start = net_io
        self.last_net_time = now

        network = {
            "upload_speed": upload_speed,
            "download_speed": download_speed,
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        }

        # Battery
        battery_percent = None
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                battery_percent = bat.percent

        # Temperatures
        temperature = None
        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # just grab the first one
                    first_temp = list(temps.values())[0][0]
                    temperature = first_temp.current
            except:
                pass

        # Processes
        processes = []
        target_apps = ["chrome.exe", "msedge.exe", "code.exe", "docker.exe", "python.exe", "node.exe", "java.exe", "studio64.exe", "postgres.exe", "redis-server.exe"]
        detected_apps = set()

        for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'exe']), key=lambda p: p.info['cpu_percent'] or 0, reverse=True)[:15]:
            try:
                info = proc.info
                name = info['name'].lower() if info['name'] else ''
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent'],
                    "memory_percent": info['memory_percent'],
                    "exe_path": info['exe']
                })
                for app in target_apps:
                    if app in name:
                        detected_apps.add(app)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # System
        try:
            uptime = (now - datetime.fromtimestamp(psutil.boot_time())).total_seconds()
        except:
            uptime = 0

        system_info = {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "uptime": uptime
        }

        return {
            "cpu": {
                "usage_percent": cpu_usage,
                "logical_cores": cpu_logical,
                "physical_cores": cpu_physical,
                "current_freq": cpu_freq.current if cpu_freq else 0,
                "max_freq": cpu_freq.max if cpu_freq else 0,
                "load_avg": load_avg
            },
            "ram": {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent
            },
            "disk": {
                "drives": disks,
                "total": total_disk,
                "used": used_disk,
                "percent": (used_disk / total_disk * 100) if total_disk > 0 else 0
            },
            "network": network,
            "battery": battery_percent,
            "temperature": temperature,
            "processes": processes,
            "applications": list(detected_apps),
            "system": system_info,
            "timestamp": now.isoformat()
        }

    async def save_telemetry(self, data):
        # Save to DB
        telemetry = await self.db.hosttelemetry.create({
            "cpuUsage": data['cpu']['usage_percent'],
            "memoryTotal": data['ram']['total'],
            "memoryUsed": data['ram']['used'],
            "memoryPercent": data['ram']['percent'],
            "diskTotal": data['disk']['total'],
            "diskUsed": data['disk']['used'],
            "diskPercent": data['disk']['percent'],
            "netSent": data['network']['bytes_sent'],
            "netRecv": data['network']['bytes_recv'],
            "batteryPercent": data['battery'],
            "temperature": data['temperature']
        })

        for p in data['processes']:
            await self.db.hostprocess.create({
                "telemetryId": telemetry.id,
                "pid": p['pid'],
                "name": p['name'] or 'unknown',
                "cpuPercent": p['cpu_percent'] or 0.0,
                "memoryPercent": p['memory_percent'] or 0.0,
                "exePath": p['exe_path']
            })

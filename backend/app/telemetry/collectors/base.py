from abc import ABC, abstractmethod
import psutil
import time

class BaseCollector(ABC):
    def get_system_metrics(self):
        return {
            'cpu': self.get_cpu(),
            'memory': self.get_memory(),
            'disk': self.get_disk(),
            'network': self.get_network(),
            'gpu': self.get_gpu(),
            'battery': self.get_battery(),
            'temperature': self.get_temperature(),
            'uptime': self.get_uptime(),
            'timestamp': time.time()
        }

    def get_cpu(self):
        freq = psutil.cpu_freq()
        return {
            'percent': psutil.cpu_percent(interval=0.1, percpu=True),
            'total_percent': psutil.cpu_percent(interval=0.1),
            'freq': freq._asdict() if freq else None,
            'cores': psutil.cpu_count(logical=False),
            'threads': psutil.cpu_count(logical=True)
        }

    def get_memory(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'percent': mem.percent,
            'used': mem.used,
            'free': mem.free,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent
        }

    def get_disk(self):
        partitions = psutil.disk_partitions(all=False)
        disks = []
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    'device': p.device,
                    'mountpoint': p.mountpoint,
                    'fstype': p.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except (PermissionError, SystemError, OSError):
                continue
        
        io = psutil.disk_io_counters()
        return {
            'partitions': disks,
            'io': io._asdict() if io else None
        }

    def get_network(self):
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout
        }
        
    def get_uptime(self):
        return time.time() - psutil.boot_time()

    def get_battery(self):
        if hasattr(psutil, 'sensors_battery'):
            batt = psutil.sensors_battery()
            if batt:
                return batt._asdict()
        return None

    @abstractmethod
    def get_gpu(self):
        pass

    @abstractmethod
    def get_temperature(self):
        pass

    @abstractmethod
    def get_services(self):
        pass

    def get_processes(self):
        processes = []
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                processes.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        processes.sort(key=lambda x: x.get('cpu_percent') or 0, reverse=True)
        return processes[:50]

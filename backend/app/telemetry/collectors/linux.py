from .base import BaseCollector
import psutil

try:
    import GPUtil
except ImportError:
    GPUtil = None

class LinuxCollector(BaseCollector):
    def get_gpu(self):
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                return [{'id': g.id, 'name': g.name, 'load': g.load, 'memoryTotal': g.memoryTotal, 'memoryUsed': g.memoryUsed, 'temperature': g.temperature} for g in gpus]
            except Exception:
                return []
        return []

    def get_temperature(self):
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            result = []
            for name, entries in temps.items():
                for entry in entries:
                    result.append({'label': entry.label or name, 'current': entry.current, 'high': entry.high, 'critical': entry.critical})
            return result
        return []

    def get_services(self):
        # Could parse systemctl list-units but keeping lightweight
        return []

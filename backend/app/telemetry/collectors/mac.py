from .base import BaseCollector
import psutil

class MacCollector(BaseCollector):
    def get_gpu(self):
        return []

    def get_temperature(self):
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            result = []
            for name, entries in temps.items():
                for entry in entries:
                    result.append({'label': entry.label or name, 'current': entry.current})
            return result
        return []

    def get_services(self):
        return []

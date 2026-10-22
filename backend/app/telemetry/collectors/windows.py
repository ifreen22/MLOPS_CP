from .base import BaseCollector
import psutil

try:
    import GPUtil
except ImportError:
    GPUtil = None

try:
    import wmi
except ImportError:
    wmi = None

class WindowsCollector(BaseCollector):
    def get_gpu(self):
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                return [{'id': g.id, 'name': g.name, 'load': g.load, 'memoryTotal': g.memoryTotal, 'memoryUsed': g.memoryUsed, 'temperature': g.temperature} for g in gpus]
            except Exception:
                return []
        return []

    def get_temperature(self):
        if wmi:
            try:
                w = wmi.WMI(namespace="root\\wmi")
                temps = w.MSAcpi_ThermalZoneTemperature()
                return [{'temperature': (t.CurrentTemperature / 10.0) - 273.15} for t in temps]
            except Exception:
                return []
        return []

    def get_services(self):
        services = []
        for s in psutil.win_service_iter():
            try:
                info = s.as_dict()
                services.append({
                    'name': info.get('name'),
                    'display_name': info.get('display_name'),
                    'status': info.get('status'),
                    'start_type': info.get('start_type')
                })
            except psutil.NoSuchProcess:
                pass
        return services

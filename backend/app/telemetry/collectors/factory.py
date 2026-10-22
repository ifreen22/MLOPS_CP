import platform
from .windows import WindowsCollector
from .linux import LinuxCollector
from .mac import MacCollector

def get_collector():
    system = platform.system().lower()
    if system == 'windows':
        return WindowsCollector()
    elif system == 'linux':
        return LinuxCollector()
    elif system == 'darwin':
        return MacCollector()
    else:
        return LinuxCollector()

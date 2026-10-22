import pytest
from unittest.mock import MagicMock, patch
from app.telemetry.collectors.factory import get_collector
from app.telemetry.collectors.windows import WindowsCollector
from app.telemetry.collectors.linux import LinuxCollector
from app.telemetry.collectors.mac import MacCollector

def test_collector_factory():
    with patch("platform.system", return_value="Windows"):
        c = get_collector()
        assert isinstance(c, WindowsCollector)

    with patch("platform.system", return_value="Linux"):
        c = get_collector()
        assert isinstance(c, LinuxCollector)

    with patch("platform.system", return_value="Darwin"):
        c = get_collector()
        assert isinstance(c, MacCollector)

    with patch("platform.system", return_value="FreeBSD"):
        c = get_collector()
        assert isinstance(c, LinuxCollector)


def test_base_collector_metrics():
    collector = WindowsCollector()
    mock_service = MagicMock()
    mock_service.as_dict.return_value = {
        "name": "wuauserv", "display_name": "Windows Update", "status": "running", "start_type": "auto"
    }

    with patch("psutil.win_service_iter", return_value=[mock_service], create=True):
        metrics = collector.get_system_metrics()
        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
        assert "network" in metrics
        assert "uptime" in metrics
        assert "timestamp" in metrics

        cpu = collector.get_cpu()
        assert "percent" in cpu
        assert "total_percent" in cpu
        assert "cores" in cpu

        mem = collector.get_memory()
        assert "total" in mem
        assert "available" in mem
        assert "percent" in mem
        assert "used" in mem

        disk = collector.get_disk()
        assert "partitions" in disk

        net = collector.get_network()
        assert "bytes_sent" in net
        assert "bytes_recv" in net

        procs = collector.get_processes()
        assert isinstance(procs, list)


def test_windows_collector_extras(monkeypatch):
    collector = WindowsCollector()

    assert collector.get_gpu() == []
    assert collector.get_temperature() == []

    mock_service = MagicMock()
    mock_service.as_dict.return_value = {
        "name": "Spooler", "display_name": "Print Spooler", "status": "running", "start_type": "auto"
    }
    with patch("psutil.win_service_iter", return_value=[mock_service]):
        services = collector.get_services()
        assert len(services) == 1
        assert services[0]["name"] == "Spooler"


def test_linux_collector_extras():
    collector = LinuxCollector()
    assert collector.get_gpu() == []
    assert collector.get_services() == []

    mock_entry = MagicMock(label="Core 0", current=45.0, high=80.0, critical=100.0)
    with patch("psutil.sensors_temperatures", return_value={"coretemp": [mock_entry]}, create=True):
        temps = collector.get_temperature()
        assert len(temps) == 1
        assert temps[0]["current"] == 45.0


def test_mac_collector_extras():
    collector = MacCollector()
    assert collector.get_gpu() == []
    assert collector.get_services() == []

    mock_entry = MagicMock(label="CPU Temp", current=42.0)
    with patch("psutil.sensors_temperatures", return_value={"cpu": [mock_entry]}, create=True):
        temps = collector.get_temperature()
        assert len(temps) == 1
        assert temps[0]["current"] == 42.0

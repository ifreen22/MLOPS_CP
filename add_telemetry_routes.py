import os

with open('backend/app/api/v1/controllers/telemetry_controller.py', 'r') as f:
    text = f.read()

append_text = """
# --- LIVE SYSTEM TELEMETRY ENDPOINTS ---
from app.telemetry.collectors import get_collector
import traceback
from fastapi import HTTPException

def safe_collect(method_name):
    collector = get_collector()
    if hasattr(collector, method_name):
        try:
            return getattr(collector, method_name)()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail='Not supported on this OS')

@router.get("/system")
async def get_system_live():
    return safe_collect('get_system_metrics')

@router.get("/cpu")
async def get_cpu_live():
    return safe_collect('get_cpu')

@router.get("/memory")
async def get_memory_live():
    return safe_collect('get_memory')

@router.get("/storage")
async def get_storage_live():
    return safe_collect('get_disk')

@router.get("/network")
async def get_network_live():
    return safe_collect('get_network')

@router.get("/processes")
async def get_processes_live():
    return safe_collect('get_processes')

@router.get("/services")
async def get_services_live():
    return safe_collect('get_services')

@router.get("/gpu")
async def get_gpu_live():
    return safe_collect('get_gpu')

@router.get("/battery")
async def get_battery_live():
    return safe_collect('get_battery')
"""

if 'get_system_live' not in text:
    with open('backend/app/api/v1/controllers/telemetry_controller.py', 'a') as f:
        f.write(append_text)

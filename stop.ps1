<#
.SYNOPSIS
    AIOps Sentinel - Graceful Teardown Script for Windows
.DESCRIPTION
    Terminates the host telemetry daemon and gracefully stops Docker containers.
.NOTES
    Run as: powershell -ExecutionPolicy Bypass -File .\stop.ps1
#>

$WorkspaceRoot = $PSScriptRoot

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "Stopping AIOps Sentinel Services..." -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan

# 1. Stop Windows Agent
Write-Host "[1/2] Terminating Windows Telemetry Agent process..." -ForegroundColor Yellow
$agentProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmd -match "windows_agent.py"
    } catch { $false }
}

if ($agentProcesses) {
    foreach ($p in $agentProcesses) {
        Write-Host "Killing process PID $($p.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $p.Id -Force
    }
    Write-Host "Telemetry Agent stopped." -ForegroundColor Green
} else {
    Write-Host "No active Telemetry Agent process found." -ForegroundColor Gray
}

# 2. Stop Docker Stack
Write-Host "[2/2] Stopping Docker Compose microservices..." -ForegroundColor Yellow
& docker compose -f "$WorkspaceRoot\docker-compose.yml" stop
Write-Host "All containers stopped gracefully. Database and metric volumes preserved." -ForegroundColor Green

Write-Host "`nTo restart services later, run:  .\run.ps1" -ForegroundColor Cyan
Write-Host "To remove containers, run:      docker compose down" -ForegroundColor Gray
Write-Host "==========================================================================`n" -ForegroundColor Cyan

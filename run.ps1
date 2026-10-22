<#
.SYNOPSIS
    AIOps Sentinel - Production Launcher Script for Windows
.DESCRIPTION
    Starts Docker Compose infrastructure services and optionally launches the
    native Windows telemetry daemon in the background.
.NOTES
    Run as: powershell -ExecutionPolicy Bypass -File .\run.ps1
#>

[CmdletBinding()]
param(
    [switch]$NoAgent
)

$WorkspaceRoot = $PSScriptRoot

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "Starting AIOps Sentinel Microservices & Telemetry..." -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan

# 1. Start Docker Containers
Write-Host "[1/2] Launching Docker Compose stack..." -ForegroundColor Yellow
& docker compose -f "$WorkspaceRoot\docker-compose.yml" up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start Docker Compose stack." -ForegroundColor Red
    exit 1
}

# 2. Launch Windows Agent
if (-not $NoAgent) {
    Write-Host "[2/2] Checking Windows Telemetry Daemon..." -ForegroundColor Yellow
    $existingAgent = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmd -match "windows_agent.py"
        } catch { $false }
    }

    if ($existingAgent) {
        Write-Host "Windows Telemetry Agent is already running (PID: $($existingAgent[0].Id))." -ForegroundColor Green
    } else {
        $pythonExe = if (Test-Path "$WorkspaceRoot\backend\.venv\Scripts\python.exe") {
            "$WorkspaceRoot\backend\.venv\Scripts\python.exe"
        } elseif (Test-Path "$WorkspaceRoot\backend\.test-venv\Scripts\python.exe") {
            "$WorkspaceRoot\backend\.test-venv\Scripts\python.exe"
        } else {
            "python"
        }

        Write-Host "Spawning Windows Telemetry Agent ($pythonExe windows_agent.py)..." -ForegroundColor Yellow
        Start-Process -FilePath $pythonExe -ArgumentList "$WorkspaceRoot\windows_agent.py" -WindowStyle Minimized
        Write-Host "Telemetry Agent successfully launched in background." -ForegroundColor Green
    }
}

Write-Host "`n==========================================================================" -ForegroundColor Green
Write-Host "AIOPS SENTINEL IS LIVE!" -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "Endpoints:" -ForegroundColor Cyan
Write-Host "  • Web Application:     http://localhost:8081  (or http://localhost:5173 for Vite dev)" -ForegroundColor White
Write-Host "  • Backend API / Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • Prometheus Server:   http://localhost:9090" -ForegroundColor White
Write-Host "  • Grafana Analytics:   http://localhost:3000 (Credentials: admin / admin)" -ForegroundColor White
Write-Host "  • Loki Logs Engine:    http://localhost:3100" -ForegroundColor White
Write-Host "`nTo check system health at any time, run: .\healthcheck.ps1" -ForegroundColor Gray
Write-Host "To stop the stack gracefully, run:       .\stop.ps1" -ForegroundColor Gray
Write-Host "==========================================================================`n" -ForegroundColor Green

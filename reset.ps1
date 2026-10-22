<#
.SYNOPSIS
    AIOps Sentinel - Clean Reset & Wipe Script
.DESCRIPTION
    Tears down Docker containers, deletes volumes (database, metrics, logs),
    and resets the local environment to a clean initial state.
.NOTES
    Run as: powershell -ExecutionPolicy Bypass -File .\reset.ps1
#>

[CmdletBinding()]
param(
    [switch]$Force
)

$WorkspaceRoot = $PSScriptRoot

Write-Host "==========================================================================" -ForegroundColor Red
Write-Host "WARNING: AIOps Sentinel Hard Reset" -ForegroundColor Red
Write-Host "==========================================================================" -ForegroundColor Red
Write-Host "This operation will:" -ForegroundColor Yellow
Write-Host "  1. Stop all Docker microservices." -ForegroundColor Yellow
Write-Host "  2. REMOVE all persistent volumes (PostgreSQL database, Prometheus history, Grafana state, Loki logs)." -ForegroundColor Yellow
Write-Host "  3. Terminate running telemetry daemons." -ForegroundColor Yellow
Write-Host "  4. Reset local databases and temporary caches." -ForegroundColor Yellow

if (-not $Force) {
    $confirm = Read-Host "Are you absolutely sure you want to proceed? (Type 'YES' to confirm)"
    if ($confirm -ne "YES") {
        Write-Host "Reset aborted by user." -ForegroundColor Green
        exit 0
    }
}

# 1. Stop Windows Agent
Write-Host "`n[1/3] Terminating host telemetry agent..." -ForegroundColor Yellow
$agentProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmd -match "windows_agent.py"
    } catch { $false }
}
if ($agentProcesses) {
    $agentProcesses | ForEach-Object { Stop-Process -Id $_.Id -Force }
}

# 2. Down Docker and remove volumes
Write-Host "[2/3] Tearing down Docker Compose containers and wiping volumes..." -ForegroundColor Yellow
& docker compose -f "$WorkspaceRoot\docker-compose.yml" down -v --remove-orphans

# 3. Clean temporary files
Write-Host "[3/3] Clearing local test caches and runtime logs..." -ForegroundColor Yellow
if (Test-Path "$WorkspaceRoot\windows-agent-runtime.log") { Remove-Item "$WorkspaceRoot\windows-agent-runtime.log" -Force }
if (Test-Path "$WorkspaceRoot\windows-agent-runtime.err.log") { Remove-Item "$WorkspaceRoot\windows-agent-runtime.err.log" -Force }
if (Test-Path "$WorkspaceRoot\backend\.pytest_cache") { Remove-Item "$WorkspaceRoot\backend\.pytest_cache" -Recurse -Force }
if (Test-Path "$WorkspaceRoot\.pytest_cache") { Remove-Item "$WorkspaceRoot\.pytest_cache" -Recurse -Force }

Write-Host "`n==========================================================================" -ForegroundColor Green
Write-Host "RESET COMPLETE. System is pristine." -ForegroundColor Green
Write-Host "To re-initialize the system from scratch, run:  .\setup.ps1" -ForegroundColor Cyan
Write-Host "==========================================================================`n" -ForegroundColor Green

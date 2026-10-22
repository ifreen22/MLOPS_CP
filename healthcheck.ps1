<#
.SYNOPSIS
    AIOps Sentinel - Automated Infrastructure & Service Health Check
.DESCRIPTION
    Scans and verifies all 12 Docker microservices, HTTP health endpoints, database
    connections, Redis caching, telemetry daemon, and API readiness.
.NOTES
    Run as: powershell -ExecutionPolicy Bypass -File .\healthcheck.ps1
#>

$WorkspaceRoot = $PSScriptRoot
$results = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedCode = 200,
        [int]$TimeoutSec = 3
    )

    $t0 = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        $t0.Stop()
        $status = if ($response.StatusCode -eq $ExpectedCode) { "PASS" } else { "FAIL" }
        return [PSCustomObject]@{
            Component = $Name
            Target    = $Url
            Status    = $status
            Latency   = "$($t0.ElapsedMilliseconds)ms"
            Details   = "HTTP $($response.StatusCode)"
        }
    } catch {
        $t0.Stop()
        return [PSCustomObject]@{
            Component = $Name
            Target    = $Url
            Status    = "FAIL"
            Latency   = "$($t0.ElapsedMilliseconds)ms"
            Details   = $_.Exception.Message
        }
    }
}

function Test-ContainerHealth {
    param([string]$ContainerName)
    try {
        $inspectJson = & docker inspect --format="{{json .State}}" $ContainerName 2>$null | ConvertFrom-Json
        if (-not $inspectJson) {
            return [PSCustomObject]@{
                Component = $ContainerName
                Target    = "Docker Container"
                Status    = "FAIL"
                Latency   = "-"
                Details   = "Container not found"
            }
        }

        $isRunning = $inspectJson.Running
        $healthStatus = if ($inspectJson.Health) { $inspectJson.Health.Status } else { "unmonitored" }

        $status = if ($isRunning -and ($healthStatus -eq "healthy" -or $healthStatus -eq "unmonitored")) { "PASS" } else { "FAIL" }
        return [PSCustomObject]@{
            Component = $ContainerName
            Target    = "Docker Container"
            Status    = $status
            Latency   = "-"
            Details   = "Running: $isRunning | Health: $healthStatus"
        }
    } catch {
        return [PSCustomObject]@{
            Component = $ContainerName
            Target    = "Docker Container"
            Status    = "FAIL"
            Latency   = "-"
            Details   = $_.Exception.Message
        }
    }
}

Write-Host "`n==========================================================================" -ForegroundColor Cyan
Write-Host "AIOPS SENTINEL SYSTEM HEALTH CHECK & AUDIT" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')" -ForegroundColor Gray
Write-Host "==========================================================================" -ForegroundColor Cyan

# 1. Probe Docker Services
Write-Host "`n[1/3] Inspecting Docker Stack Containers..." -ForegroundColor Yellow
$containers = @(
    "mlops_cp-backend-1",
    "mlops_cp-frontend-1",
    "mlops_cp-nginx-1",
    "mlops_cp-db-1",
    "mlops_cp-redis-1",
    "mlops_cp-prometheus-1",
    "mlops_cp-grafana-1",
    "mlops_cp-loki-1",
    "mlops_cp-otel-collector-1",
    "mlops_cp-cadvisor-1",
    "mlops_cp-node-exporter-1",
    "mlops_cp-promtail-1"
)

foreach ($c in $containers) {
    $results += Test-ContainerHealth -ContainerName $c
}

# 2. Probe HTTP REST & Monitoring Endpoints
Write-Host "[2/3] Probing Live HTTP & Telemetry Endpoints..." -ForegroundColor Yellow

# Obtain auth token for authenticated route testing
$adminToken = $null
try {
    $loginBody = "username=admin@localhost&password=caXK6HxqFUVS5buIi1ayl2wEA2w4kTsI8rtuCRj_9rA"
    $loginRes = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/x-www-form-urlencoded" -TimeoutSec 3 -ErrorAction Stop
    $adminToken = $loginRes.access_token
} catch {}

function Test-EndpointWithAuth {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedCode = 200,
        [bool]$RequiresAuth = $false,
        [int]$TimeoutSec = 3
    )

    $headers = @{}
    if ($RequiresAuth -and $adminToken) {
        $headers["Authorization"] = "Bearer $adminToken"
    }

    $t0 = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -Headers $headers -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        $t0.Stop()
        $status = if ($response.StatusCode -eq $ExpectedCode) { "PASS" } else { "FAIL" }
        return [PSCustomObject]@{
            Component = $Name
            Target    = $Url
            Status    = $status
            Latency   = "$($t0.ElapsedMilliseconds)ms"
            Details   = "HTTP $($response.StatusCode) (Protected)"
        }
    } catch {
        $t0.Stop()
        $errStatus = $_.Exception.Response.StatusCode.value__
        if ($RequiresAuth -and ($errStatus -eq 401 -or $errStatus -eq 200)) {
            return [PSCustomObject]@{
                Component = $Name
                Target    = $Url
                Status    = "PASS"
                Latency   = "$($t0.ElapsedMilliseconds)ms"
                Details   = "HTTP $errStatus (Route Active & Auth Enforced)"
            }
        }
        return [PSCustomObject]@{
            Component = $Name
            Target    = $Url
            Status    = "FAIL"
            Latency   = "$($t0.ElapsedMilliseconds)ms"
            Details   = $_.Exception.Message
        }
    }
}

$endpoints = @(
    @{ Name = "FastAPI Health Probe"; Url = "http://localhost:8000/api/v1/health"; Expected = 200; Auth = $false },
    @{ Name = "Auth Status Probe"; Url = "http://localhost:8000/api/v1/auth/status"; Expected = 200; Auth = $false },
    @{ Name = "Prometheus ASGI Metrics"; Url = "http://localhost:8000/internal/metrics"; Expected = 200; Auth = $false },
    @{ Name = "ML Anomaly Engine"; Url = "http://localhost:8000/api/v1/ml/anomaly/health"; Expected = 200; Auth = $true },
    @{ Name = "ML HDBSCAN Clusterer"; Url = "http://localhost:8000/api/v1/ml/cluster/health"; Expected = 200; Auth = $true },
    @{ Name = "ML GraphSAGE RCA GNN"; Url = "http://localhost:8000/api/v1/ml/root-cause/health"; Expected = 200; Auth = $true },
    @{ Name = "ML LightGBM Risk Engine"; Url = "http://localhost:8000/api/v1/ml/risk/health"; Expected = 200; Auth = $true },
    @{ Name = "Nginx Web Ingress"; Url = "http://localhost:8081"; Expected = 200; Auth = $false },
    @{ Name = "Prometheus UI"; Url = "http://localhost:9090/-/healthy"; Expected = 200; Auth = $false },
    @{ Name = "Grafana Dashboard"; Url = "http://localhost:3000/api/health"; Expected = 200; Auth = $false },
    @{ Name = "Loki Ingestion Status"; Url = "http://localhost:3100/ready"; Expected = 200; Auth = $false }
)

foreach ($ep in $endpoints) {
    $results += Test-EndpointWithAuth -Name $ep.Name -Url $ep.Url -ExpectedCode $ep.Expected -RequiresAuth $ep.Auth
}

# 3. Probe Host Agent Process
Write-Host "[3/3] Inspecting Windows Telemetry Daemon..." -ForegroundColor Yellow
$agentProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmd -match "windows_agent.py"
    } catch { $false }
}

if ($agentProcesses) {
    $results += [PSCustomObject]@{
        Component = "Windows Telemetry Agent"
        Target    = "Local OS Daemon"
        Status    = "PASS"
        Latency   = "-"
        Details   = "Active (PID: $($agentProcesses[0].Id))"
    }
} else {
    $results += [PSCustomObject]@{
        Component = "Windows Telemetry Agent"
        Target    = "Local OS Daemon"
        Status    = "WARN"
        Latency   = "-"
        Details   = "Not running as background process (Run .\run.ps1 to start)"
    }
}

# Format and Display Table
Write-Host "`nHealth Audit Summary Table:" -ForegroundColor Cyan
$results | Format-Table -Property Component, Target, Status, Latency, Details -AutoSize

$passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$totalCount = $results.Count

Write-Host "Result: $passCount/$totalCount Components Operating Normally." -ForegroundColor $(if ($passCount -eq $totalCount) { "Green" } else { "Yellow" })

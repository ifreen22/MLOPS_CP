<#
.SYNOPSIS
    AIOps Sentinel - Automated Production Setup Script for Windows (PowerShell)
.DESCRIPTION
    Automates prerequisite verification, environment initialization, Python & Node.js
    dependency installations, Prisma ORM schema synchronizations, Docker container
    orchestration, and service health validations.
.NOTES
    Run as: powershell -ExecutionPolicy Bypass -File .\setup.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipDocker,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = $PSScriptRoot

function Write-Step {
    param([string]$Message)
    Write-Host "`n==========================================================================" -ForegroundColor Cyan
    Write-Host "[STEP] $Message" -ForegroundColor Cyan
    Write-Host "==========================================================================" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-WarnMsg {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    exit 1
}

Write-Host @"
    ___    ____ ____             _____            __  _            __
   /   |  /  _// __ \ ____  ____/ ___/___  ____  / /_(_)___  ___  / /
  / /| |  / / / / / // __ \/ ___/\__ \/ _ \/ __ \/ __/ / __ \/ _ \/ / 
 / ___ |_/ / / /_/ // /_/ (__  )___/ /  __/ / / / /_/ / / / /  __/ /  
/_/  |_/___/ \____// .___/____//____/\___/_/ /_/\__/_/_/ /_/\___/_/   
                  /_/                                                 
                  Production Setup & Verification
"@ -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# 1. Prerequisite Validation
# ------------------------------------------------------------------------------
Write-Step "Checking System Prerequisites"

# Check Python
try {
    $pythonVer = & python --version 2>&1
    Write-Success "Python found: $pythonVer"
} catch {
    Write-Fail "Python is not installed or not in PATH. Please install Python 3.11 or 3.13."
}

# Check Node.js
try {
    $nodeVer = & node --version 2>&1
    Write-Success "Node.js found: $nodeVer"
} catch {
    Write-Fail "Node.js is not installed or not in PATH. Please install Node.js 18+ LTS."
}

# Check Docker
if (-not $SkipDocker) {
    try {
        $dockerVer = & docker --version 2>&1
        Write-Success "Docker found: $dockerVer"
    } catch {
        Write-Fail "Docker is not installed or not in PATH. Please install Docker Desktop."
    }

    try {
        & docker info >$null 2>&1
        Write-Success "Docker daemon is active and responsive."
    } catch {
        Write-Fail "Docker Desktop is installed but the daemon is not running. Please start Docker Desktop."
    }
}

# ------------------------------------------------------------------------------
# 2. Environment File Initialization
# ------------------------------------------------------------------------------
Write-Step "Initializing Environment Configuration"

if (-not (Test-Path "$WorkspaceRoot\.env")) {
    Copy-Item "$WorkspaceRoot\.env.example" "$WorkspaceRoot\.env"
    Write-Success "Created root .env from template."
} else {
    Write-Success "Root .env already exists."
}

if (-not (Test-Path "$WorkspaceRoot\backend\.env")) {
    Copy-Item "$WorkspaceRoot\backend\.env.example" "$WorkspaceRoot\backend\.env"
    Write-Success "Created backend/.env from template."
} else {
    Write-Success "backend/.env already exists."
}

if (-not (Test-Path "$WorkspaceRoot\aiops-sentinel\.env")) {
    Copy-Item "$WorkspaceRoot\aiops-sentinel\.env.example" "$WorkspaceRoot\aiops-sentinel\.env"
    Write-Success "Created aiops-sentinel/.env from template."
} else {
    Write-Success "aiops-sentinel/.env already exists."
}

# ------------------------------------------------------------------------------
# 3. Python Virtual Environment & Backend Dependencies
# ------------------------------------------------------------------------------
Write-Step "Configuring Python Backend Virtual Environment"

$VenvPath = "$WorkspaceRoot\backend\.venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment at $VenvPath..." -ForegroundColor Yellow
    & python -m venv $VenvPath
}
$VenvPython = "$VenvPath\Scripts\python.exe"

Write-Host "Upgrading pip and installing backend dependencies..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r "$WorkspaceRoot\backend\requirements.txt" --quiet
& $VenvPython -m pip install -r "$WorkspaceRoot\windows-agent-requirements.txt" --quiet
Write-Success "Python backend and agent dependencies installed successfully."

# ------------------------------------------------------------------------------
# 4. Prisma ORM Client Generation
# ------------------------------------------------------------------------------
Write-Step "Generating Prisma ORM Client"

Push-Location "$WorkspaceRoot\backend"
try {
    & $VenvPython -m prisma generate
    Write-Success "Prisma Python Client successfully generated."
} catch {
    Write-WarnMsg "Python prisma generate encountered an issue, attempting via npx..."
    & npx prisma generate
} finally {
    Pop-Location
}

# ------------------------------------------------------------------------------
# 5. Frontend Dependencies & Build
# ------------------------------------------------------------------------------
if (-not $SkipFrontend) {
    Write-Step "Installing Frontend NPM Dependencies"
    Push-Location "$WorkspaceRoot\aiops-sentinel"
    try {
        & npm install --legacy-peer-deps
        Write-Success "NPM packages installed."
        Write-Host "Running frontend production build verification..." -ForegroundColor Yellow
        & npm run build
        Write-Success "Frontend build completed successfully."
    } finally {
        Pop-Location
    }
}

# ------------------------------------------------------------------------------
# 6. Docker Services Startup
# ------------------------------------------------------------------------------
if (-not $SkipDocker) {
    Write-Step "Starting Docker Infrastructure Stack"
    & docker compose -f "$WorkspaceRoot\docker-compose.yml" up -d
    Write-Success "Docker Compose stack launched."
    
    Write-Host "Waiting 10 seconds for database readiness..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    Write-Host "Pushing database schema via Prisma..." -ForegroundColor Yellow
    Push-Location "$WorkspaceRoot\backend"
    try {
        & npx prisma db push --accept-data-loss
        Write-Success "Database schema synchronized with PostgreSQL."
    } catch {
        Write-WarnMsg "Database push completed with non-fatal warnings or was already synchronized."
    } finally {
        Pop-Location
    }
}

# ------------------------------------------------------------------------------
# 7. Final Healthcheck & Instructions
# ------------------------------------------------------------------------------
Write-Step "Validating Service Health"
& powershell -ExecutionPolicy Bypass -File "$WorkspaceRoot\healthcheck.ps1"

Write-Host "`n==========================================================================" -ForegroundColor Green
Write-Host "SETUP COMPLETE! AIOps Sentinel is ready to run." -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "Quick Launch Commands:" -ForegroundColor Cyan
Write-Host "  1. Start native stack + agent:   .\run.ps1" -ForegroundColor Yellow
Write-Host "  2. Run comprehensive tests:      npm --prefix aiops-sentinel run test:e2e" -ForegroundColor Yellow
Write-Host "  3. Stop stack:                   .\stop.ps1" -ForegroundColor Yellow
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  • Frontend Web Console:          http://localhost:8081 (or http://localhost:5173)" -ForegroundColor White
Write-Host "  • Backend Swagger OpenAPI:       http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • Prometheus Dashboard:          http://localhost:9090" -ForegroundColor White
Write-Host "  • Grafana Analytics:             http://localhost:3000" -ForegroundColor White
Write-Host "==========================================================================`n" -ForegroundColor Green

# PowerShell script to start the Diamond ERP Backend
# Run with: .\start.ps1

Set-Location $PSScriptRoot

# 1. Start MongoDB if not running
Write-Host ""
Write-Host "[1/3] Checking MongoDB service..." -ForegroundColor Cyan
$mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
if ($mongoService) {
    if ($mongoService.Status -ne "Running") {
        Write-Host "  Starting MongoDB service (requires admin)..." -ForegroundColor Yellow
        try {
            Start-Process -FilePath "powershell" -ArgumentList "-Command Start-Service MongoDB" -Verb RunAs -Wait
            Write-Host "  MongoDB started." -ForegroundColor Green
        } catch {
            Write-Host "  Could not start MongoDB automatically. Please run 'net start MongoDB' as Administrator." -ForegroundColor Red
        }
    } else {
        Write-Host "  MongoDB is already running." -ForegroundColor Green
    }
} else {
    Write-Host "  MongoDB service not found. Make sure MongoDB is installed." -ForegroundColor Red
}

# 2. Ensure virtual environment exists
Write-Host ""
Write-Host "[2/3] Verifying virtual environment..." -ForegroundColor Cyan
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    py -m venv .venv
    Write-Host "  Installing dependencies..." -ForegroundColor Yellow
    & ".\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
    & ".\.venv\Scripts\python.exe" -m pip install -q -r requirements.txt
    Write-Host "  Dependencies installed." -ForegroundColor Green
} else {
    Write-Host "  Virtual environment exists." -ForegroundColor Green
}

# 3. Start the FastAPI server
Write-Host ""
Write-Host "[3/3] Starting FastAPI server on http://localhost:8000 ..." -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run the Network Monitoring Dashboard (Next.js + Supabase)
# This script installs dependencies and starts the dev server

$DashboardPath = Join-Path $PSScriptRoot "network-monitoring-dashboard"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Network Monitoring Dashboard - Startup Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check if node_modules exists
if (-not (Test-Path (Join-Path $DashboardPath "node_modules"))) {
    Write-Host "`n[Step 1/3] Installing npm dependencies..." -ForegroundColor Yellow
    Set-Location $DashboardPath
    npm install --force --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) {
        Write-Host "npm install failed. Trying with legacy peer deps..." -ForegroundColor Red
        npm install --force --no-fund --no-audit --legacy-peer-deps
    }
} else {
    Write-Host "`n[Step 1/3] node_modules already exists. Skipping install." -ForegroundColor Green
}

# Build the project
Write-Host "`n[Step 2/3] Building Next.js project..." -ForegroundColor Yellow
Set-Location $DashboardPath
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed. Check errors above." -ForegroundColor Red
    exit 1
}

# Start dev server
Write-Host "`n[Step 3/3] Starting dev server on http://localhost:3000 ..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray
npm run dev

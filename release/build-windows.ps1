$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== eli_lab Pattern Generator / Windows ONEFILE build ==" -ForegroundColor Cyan

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Project virtual environment not found: $Python`nCreate it first with: python -m venv .venv"
}

Write-Host "Python: $(& $Python --version)"

Write-Host "Installing build dependencies..." -ForegroundColor Yellow
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements-dev.txt

Write-Host "Running tests..." -ForegroundColor Yellow
& $Python -m pytest

Write-Host "Cleaning previous PyInstaller output..." -ForegroundColor Yellow
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root "build")
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root "dist")
New-Item -ItemType Directory -Force (Join-Path $Root "dist") | Out-Null

Write-Host "Building ONEFILE Windows executable..." -ForegroundColor Yellow
& $Python -m PyInstaller --noconfirm --clean (Join-Path $Root "release\eli_lab_pattern_generator.spec")

$Exe = Join-Path $Root "dist\eli_lab-pattern-generator.exe"

if (-not (Test-Path $Exe)) {
    throw "PyInstaller completed but the one-file executable was not found: $Exe"
}

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "Executable: $Exe"
Write-Host ""
Write-Host "This is the complete standalone application. Nothing else from dist is required." -ForegroundColor Cyan

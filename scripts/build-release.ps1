$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host '== eli_lab Pattern Generator release build ==' -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python was not found on PATH.'
}

Write-Host "Python: $(& python --version)"

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Creating .venv...' -ForegroundColor Yellow
    & python -m venv .venv
}

$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'

Write-Host 'Installing release dependencies...' -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements-dev.txt

Write-Host 'Running tests...' -ForegroundColor Yellow
& $VenvPython -m pytest

Write-Host 'Cleaning previous build output...' -ForegroundColor Yellow
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'build')
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'dist')
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'release\artifacts')
New-Item -ItemType Directory -Force (Join-Path $Root 'release\artifacts') | Out-Null

Write-Host 'Building Python distributions...' -ForegroundColor Yellow
& $VenvPython -m build --outdir release/artifacts

Write-Host 'Building Windows portable application...' -ForegroundColor Yellow
& $VenvPython -m PyInstaller --noconfirm --clean release/eli_lab_pattern_generator.spec

$DistDir = Join-Path $Root 'dist\eli_lab-pattern-generator'
$ZipPath = Join-Path $Root 'release\artifacts\eli_lab-pattern-generator-windows-x64.zip'

if (-not (Test-Path $DistDir)) {
    throw "PyInstaller output was not found: $DistDir"
}

if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}

Write-Host 'Creating portable ZIP...' -ForegroundColor Yellow
Compress-Archive -Path (Join-Path $DistDir '*') -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host ''
Write-Host 'Release artifacts:' -ForegroundColor Green
Get-ChildItem (Join-Path $Root 'release\artifacts') | Select-Object Name, Length | Format-Table -AutoSize

Write-Host ''
Write-Host 'Build completed successfully.' -ForegroundColor Green

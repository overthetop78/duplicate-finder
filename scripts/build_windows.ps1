param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "[1/3] Installation des dependances de build"
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt -r requirements-build.txt

Write-Host "[2/3] Nettoyage"
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

Write-Host "[3/3] Build Windows autonome (.exe onefile)"
& $PythonExe -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onefile `
  --name duplicate-finder `
  --hidden-import openpyxl `
  --hidden-import xlrd `
  --hidden-import odf `
  --hidden-import pandas `
  src/main.py

Write-Host "Build termine: dist/duplicate-finder.exe"

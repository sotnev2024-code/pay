#Requires -Version 5.1
<#
.SYNOPSIS
    Запускает Caddy (HTTPS) и бота. Caddy работает в фоне, бот — в текущем окне.
    Остановка: Ctrl+C (Caddy завершится автоматически).
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    $ProjectRoot = (Get-Location).Path
}

$CaddyDir = Join-Path $ProjectRoot "caddy"
$CaddyExe = Join-Path $CaddyDir "caddy.exe"
$CaddyfilePath = Join-Path $ProjectRoot "Caddyfile"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) { $PythonExe = "python" }
$MainPy = Join-Path $ProjectRoot "main.py"

if (-not (Test-Path $CaddyExe)) {
    Write-Host 'Run .\scripts\setup-https.ps1 first.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $CaddyfilePath)) {
    Write-Host 'Caddyfile not found. Run .\scripts\setup-https.ps1' -ForegroundColor Red
    exit 1
}

$caddyProcess = $null
try {
    Write-Host 'Starting Caddy (HTTPS)...' -ForegroundColor Cyan
    $caddyProc = Start-Process -FilePath $CaddyExe -ArgumentList 'run','--config',$CaddyfilePath -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden
    $caddyProcess = $caddyProc
    Start-Sleep -Seconds 2
    if ($caddyProc.HasExited) {
        Write-Host 'Caddy exited. Check Caddyfile and ports 80/443.' -ForegroundColor Red
        exit 1
    }
    Write-Host ('Caddy started PID ' + $caddyProc.Id) -ForegroundColor Green
    Write-Host 'Starting bot...' -ForegroundColor Cyan
    & $PythonExe $MainPy
} finally {
    if ($caddyProcess -and -not $caddyProcess.HasExited) {
        Write-Host 'Stopping Caddy...' -ForegroundColor Yellow
        $caddyProcess.Kill()
        Write-Host 'Caddy stopped.' -ForegroundColor Green
    }
}

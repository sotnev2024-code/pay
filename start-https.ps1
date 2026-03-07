#Requires -Version 5.1
<#
.SYNOPSIS
    Настраивает HTTPS (Caddy + сертификат) и запускает бота.
    При первом запуске: скачивает Caddy, создаёт Caddyfile из .env, обновляет .env для HTTPS.
    Дальше: запускает Caddy и бота.
.EXAMPLE
    .\start-https.ps1
    Запуск из корня проекта (папка pay).
.NOTES
    В .env должны быть указаны WEBAPP_URL и WEBHOOK_URL с вашим доменом.
    На роутере пробросьте порты 80 и 443 на этот компьютер.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }

$SetupScript = Join-Path $ProjectRoot "scripts\setup-https.ps1"
$RunScript   = Join-Path $ProjectRoot "scripts\run-with-https.ps1"

if (-not (Test-Path $SetupScript)) {
    Write-Host "Не найден scripts\setup-https.ps1. Запускайте из корня проекта (pay)." -ForegroundColor Red
    exit 1
}

# Один раз настраиваем (caddy + Caddyfile + .env)
& $SetupScript

# Запускаем Caddy + бота
& $RunScript

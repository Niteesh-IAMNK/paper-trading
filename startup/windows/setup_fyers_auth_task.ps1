# FYERS Auth Utility — Windows Task Scheduler setup
#
# Run this script once from an elevated PowerShell session to register a
# daily startup task. It does NOT run automatically; review paths first.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File startup\windows\setup_fyers_auth_task.ps1
#
# Optional parameters:
#   -ProjectRoot "C:\path\to\project"
#   -TaskName "FYERS Auth Token Renewal"
#   -RunAtLogon   # also trigger at user logon (default: daily at 08:00)

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$TaskName = "FYERS Auth Token Renewal",
    [switch]$RunAtLogon
)

$ErrorActionPreference = "Stop"

$BatchFile = Join-Path $ProjectRoot "startup\windows\run_fyers_auth.bat"
$LogDir = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $BatchFile)) {
    throw "Batch launcher not found: $BatchFile"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Action = New-ScheduledTaskAction `
    -Execute $BatchFile `
    -WorkingDirectory $ProjectRoot

if ($RunAtLogon) {
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
} else {
    # Daily before Indian market open (adjust for your timezone)
    $Trigger = New-ScheduledTaskTrigger -Daily -At "08:00"
}

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Renews FYERS API access token via auth_helper utility." `
    -Force

Write-Host "Scheduled task registered: $TaskName"
Write-Host "Project root: $ProjectRoot"
Write-Host "Launcher: $BatchFile"
Write-Host ""
Write-Host "Prerequisites:"
Write-Host "  1. pip install -r auth_helper\requirements.txt"
Write-Host "  2. playwright install msedge"
Write-Host "  3. Configure .env with FYERS_* credentials"

param(
    [string]$UsbipdPath = "C:\Program Files\usbipd-win\usbipd.exe",
    [string]$BusId = "2-2",
    [string]$HardwareId = "1A86:7523",
    [string]$Distro = "Ubuntu-22.04",
    [switch]$RestartUsbipdService,
    [switch]$NoAttach,
    [switch]$WhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-Usbipd {
    param([string[]]$Arguments)
    & $UsbipdPath @Arguments
}

function Write-Step {
    param([string]$Message)
    Write-Host "[usbipd-recover] $Message"
}

if (-not (Test-Path -LiteralPath $UsbipdPath)) {
    throw "usbipd executable not found at '$UsbipdPath'"
}

if (-not (Test-IsAdministrator)) {
    throw @"
Administrator privileges are required for usbipd unbind/bind/attach and service restart.

Open Windows Terminal or PowerShell as Administrator, then rerun either:

  wsl -d $Distro
  cd /home/muqiao/dev/ros2/workspaces/so101_ws
  bash tools/hardware/attach_main_arm_com4_to_wsl.sh --restart-service

Or run directly in elevated PowerShell:

  & '$UsbipdPath' unbind --busid $BusId
  Restart-Service usbipd -Force
  & '$UsbipdPath' bind --busid $BusId
  & '$UsbipdPath' attach --wsl $Distro --busid $BusId --auto-attach
"@
}

Write-Step "usbipd path: $UsbipdPath"
Write-Step "target busid=$BusId hardwareId=$HardwareId distro=$Distro"

Write-Step "current usbipd list:"
Invoke-Usbipd @("list")

if ($WhatIf) {
    Write-Step "WhatIf enabled. Planned actions:"
    Write-Host "  1. usbipd unbind --busid $BusId"
    if ($RestartUsbipdService) {
        Write-Host "  2. Restart-Service usbipd"
        Write-Host "  3. Start-Sleep 2"
        Write-Host "  4. usbipd bind --busid $BusId"
        if (-not $NoAttach) {
            Write-Host "  5. usbipd attach --wsl $Distro --busid $BusId --auto-attach"
        }
    } else {
        Write-Host "  2. usbipd bind --busid $BusId"
        if (-not $NoAttach) {
            Write-Host "  3. usbipd attach --wsl $Distro --busid $BusId --auto-attach"
        }
    }
    exit 0
}

Write-Step "unbinding current shared state for busid $BusId"
Invoke-Usbipd @("unbind", "--busid", $BusId)

if ($RestartUsbipdService) {
    Write-Step "restarting Windows service usbipd"
    Restart-Service -Name "usbipd" -Force
    Start-Sleep -Seconds 2
}

Write-Step "binding device back into shareable state"
Invoke-Usbipd @("bind", "--busid", $BusId)

if (-not $NoAttach) {
    Write-Step "attaching device to WSL distro $Distro"
    Invoke-Usbipd @("attach", "--wsl", $Distro, "--busid", $BusId, "--auto-attach")
}

Write-Step "final usbipd list:"
Invoke-Usbipd @("list")

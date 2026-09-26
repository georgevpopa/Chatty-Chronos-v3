<#
.SYNOPSIS
Installs WSL2, Docker Desktop, and sets up Chatty-Chronos-v2.

.DESCRIPTION
This script automates the installation of WSL2 (Windows Subsystem for Linux),
Ubuntu distribution, Docker Desktop, and runs the initial setup for Chatty-Chronos-v2
using docker-compose. Run this script as Administrator.
#>

param (
    [switch]$InstallDocker = $true
)

# Ensure script is running as Administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "This script requires Administrator privileges to install WSL and Docker. Please restart PowerShell as Administrator."
    exit
}

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Chatty-Chronos-v2 WSL & Docker Installer  " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Install WSL if not present
$wslStatus = wsl --status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[1/4] WSL not found. Installing WSL2..." -ForegroundColor Yellow
    wsl --install --no-distribution
    Write-Host "WSL installation triggered. PLEASE RESTART YOUR COMPUTER and run this script again." -ForegroundColor Red
    exit
} else {
    Write-Host "`n[1/4] WSL is already installed." -ForegroundColor Green
}

# 2. Check/Install Ubuntu
$distro = wsl -l -q | Select-String "Ubuntu"
if (-not $distro) {
    Write-Host "`n[2/4] Installing Ubuntu for WSL..." -ForegroundColor Yellow
    wsl --install -d Ubuntu
} else {
    Write-Host "`n[2/4] Ubuntu distribution already installed." -ForegroundColor Green
}

# 3. Optional: Install Docker Desktop
if ($InstallDocker) {
    $dockerCheck = Get-Command "docker" -ErrorAction SilentlyContinue
    if (-not $dockerCheck) {
        Write-Host "`n[3/4] Downloading Docker Desktop..." -ForegroundColor Yellow
        $installerPath = "$env:TEMP\DockerInstaller.exe"
        Invoke-WebRequest -Uri "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -OutFile $installerPath
        
        Write-Host "Installing Docker Desktop. This may take a while..." -ForegroundColor Yellow
        Start-Process -FilePath $installerPath -ArgumentList "install", "--quiet", "--accept-license" -Wait -NoNewWindow
        Write-Host "Docker Desktop installed." -ForegroundColor Green
    } else {
        Write-Host "`n[3/4] Docker is already installed." -ForegroundColor Green
    }
} else {
    Write-Host "`n[3/4] Skipping Docker Desktop installation as requested." -ForegroundColor DarkGray
}

# 4. Check Docker Daemon & Build App
Write-Host "`n[4/4] Checking Docker daemon status..." -ForegroundColor Yellow
# Give Docker a moment to start if it was just installed
Start-Sleep -Seconds 5

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker daemon is not running. Please open Docker Desktop manually, ensure it finishes starting, and run this script again." -ForegroundColor Red
} else {
    Write-Host "Docker daemon is running." -ForegroundColor Green
    
    Write-Host "`nStarting Chatty-Chronos via Docker Compose..." -ForegroundColor Cyan
    docker-compose up -d --build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n=============================================" -ForegroundColor Cyan
        Write-Host "Deployment successful!" -ForegroundColor Green
        Write-Host "Run 'docker-compose logs -f' to view logs." -ForegroundColor Green
        Write-Host "=============================================" -ForegroundColor Cyan
    } else {
        Write-Host "`nDeployment encountered an error. Please check the output above." -ForegroundColor Red
    }
}

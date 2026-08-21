# AIOps Monitoring Stack Deployment Script (PowerShell)
# =====================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("install", "start", "stop", "restart", "status", "logs", "reload", "backup", "restore", "help")]
    [string]$Command = "help",
    
    [Parameter(Mandatory=$false)]
    [string]$Service,
    
    [Parameter(Mandatory=$false)]
    [string]$BackupDir
)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $ScriptDir "docker-compose.yml"
$EnvFile = Join-Path $ScriptDir ".env"

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed. Please install Docker Desktop first."
        exit 1
    }
    
    # Check Docker Compose
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue) -and 
        -not (docker compose version 2>&1 | Select-String "version")) {
        Write-Error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    }
    
    Write-Info "Prerequisites check passed."
}

function New-EnvFile {
    if (-not (Test-Path $EnvFile)) {
        Write-Info "Creating .env file with default values..."
        @"
# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# PostgreSQL Exporter Configuration
POSTGRES_DATA_SOURCE_NAME=postgresql://user:password@host.docker.internal:5432/aiops?sslmode=disable

# Redis Exporter Configuration
REDIS_ADDR=redis://host.docker.internal:6379

# SMTP Configuration (for email alerts)
SMTP_SERVER=localhost:587
SMTP_FROM=alertmanager@aiops.local
SMTP_USERNAME=
SMTP_PASSWORD=

# Email Recipients
DEFAULT_EMAIL=admin@aiops.local
CRITICAL_EMAIL=oncall@aiops.local
WARNING_EMAIL=ops@aiops.local
SLO_EMAIL=sre@aiops.local
PERFORMANCE_EMAIL=perf@aiops.local
RESOURCE_EMAIL=infra@aiops.local
DATABASE_EMAIL=dba@aiops.local

# Slack Configuration (for Slack alerts)
SLACK_WEBHOOK_URL=
SLACK_CRITICAL_CHANNEL=#aiops-critical
SLACK_WARNING_CHANNEL=#aiops-ops
SLACK_SLO_CHANNEL=#aiops-sre
"@ | Out-File -FilePath $EnvFile -Encoding UTF8
        Write-Warning "Please edit $EnvFile with your actual configuration values."
    } else {
        Write-Info ".env file already exists."
    }
}

function New-Directories {
    Write-Info "Creating necessary directories..."
    
    $directories = @(
        (Join-Path $ScriptDir "prometheus\alerts"),
        (Join-Path $ScriptDir "grafana\provisioning\datasources"),
        (Join-Path $ScriptDir "grafana\provisioning\dashboards"),
        (Join-Path $ScriptDir "grafana\dashboards"),
        (Join-Path $ScriptDir "alertmanager"),
        (Join-Path $ScriptDir "caddy")
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Info "Directories created."
}

function New-CaddyConfig {
    $caddyFile = Join-Path $ScriptDir "caddy\Caddyfile"
    
    if (-not (Test-Path $caddyFile)) {
        Write-Info "Creating Caddy configuration..."
        @"
{
    email admin@aiops.local
}

:80 {
    reverse_proxy prometheus:9090
    reverse_proxy grafana:3000
    reverse_proxy alertmanager:9093
}
"@ | Out-File -FilePath $caddyFile -Encoding UTF8
        Write-Info "Caddy configuration created."
    } else {
        Write-Info "Caddy configuration already exists."
    }
}

function Start-Services {
    Write-Info "Starting monitoring stack..."
    
    if (docker compose version 2>&1 | Select-String "version") {
        docker compose -f $ComposeFile up -d
    } else {
        docker-compose -f $ComposeFile up -d
    }
    
    Write-Info "Monitoring stack started."
}

function Stop-Services {
    Write-Info "Stopping monitoring stack..."
    
    if (docker compose version 2>&1 | Select-String "version") {
        docker compose -f $ComposeFile down
    } else {
        docker-compose -f $ComposeFile down
    }
    
    Write-Info "Monitoring stack stopped."
}

function Restart-Services {
    Write-Info "Restarting monitoring stack..."
    
    if (docker compose version 2>&1 | Select-String "version") {
        docker compose -f $ComposeFile restart
    } else {
        docker-compose -f $ComposeFile restart
    }
    
    Write-Info "Monitoring stack restarted."
}

function Get-ServiceStatus {
    Write-Info "Checking service status..."
    
    if (docker compose version 2>&1 | Select-String "version") {
        docker compose -f $ComposeFile ps
    } else {
        docker-compose -f $ComposeFile ps
    }
}

function Show-Logs {
    if ([string]::IsNullOrEmpty($Service)) {
        Write-Info "Showing logs for all services..."
        if (docker compose version 2>&1 | Select-String "version") {
            docker compose -f $ComposeFile logs -f
        } else {
            docker-compose -f $ComposeFile logs -f
        }
    } else {
        Write-Info "Showing logs for $Service..."
        if (docker compose version 2>&1 | Select-String "version") {
            docker compose -f $ComposeFile logs -f $Service
        } else {
            docker-compose -f $ComposeFile logs -f $Service
        }
    }
}

function Reload-Prometheus {
    Write-Info "Reloading Prometheus configuration..."
    
    try {
        Invoke-WebRequest -Uri "http://localhost:9090/-/reload" -Method POST -UseBasicParsing | Out-Null
        Write-Info "Prometheus configuration reloaded."
    } catch {
        Write-Error "Failed to reload Prometheus: $_"
    }
}

function Backup-Data {
    $backupDir = Join-Path $ScriptDir "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    
    Write-Info "Creating backup at $backupDir..."
    
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Backup Prometheus data
    if (docker ps | Select-String "aiops-prometheus") {
        docker exec aiops-prometheus tar czf - /prometheus | Out-File -FilePath "$backupDir\prometheus-data.tar.gz" -Encoding Byte
    }
    
    # Backup Grafana data
    if (docker ps | Select-String "aiops-grafana") {
        docker exec aiops-grafana tar czf - /var/lib/grafana | Out-File -FilePath "$backupDir\grafana-data.tar.gz" -Encoding Byte
    }
    
    # Backup Alertmanager data
    if (docker ps | Select-String "aiops-alertmanager") {
        docker exec aiops-alertmanager tar czf - /alertmanager | Out-File -FilePath "$backupDir\alertmanager-data.tar.gz" -Encoding Byte
    }
    
    Write-Info "Backup completed."
}

function Restore-Data {
    if ([string]::IsNullOrEmpty($BackupDir)) {
        Write-Error "Please specify backup directory using -BackupDir parameter."
        exit 1
    }
    
    if (-not (Test-Path $BackupDir)) {
        Write-Error "Backup directory does not exist: $BackupDir"
        exit 1
    }
    
    Write-Info "Restoring data from $BackupDir..."
    
    # Restore Prometheus data
    $prometheusBackup = Join-Path $BackupDir "prometheus-data.tar.gz"
    if (Test-Path $prometheusBackup) {
        Get-Content $prometheusBackup -Raw | docker exec -i aiops-prometheus tar xzf -
    }
    
    # Restore Grafana data
    $grafanaBackup = Join-Path $BackupDir "grafana-data.tar.gz"
    if (Test-Path $grafanaBackup) {
        Get-Content $grafanaBackup -Raw | docker exec -i aiops-grafana tar xzf -
    }
    
    # Restore Alertmanager data
    $alertmanagerBackup = Join-Path $BackupDir "alertmanager-data.tar.gz"
    if (Test-Path $alertmanagerBackup) {
        Get-Content $alertmanagerBackup -Raw | docker exec -i aiops-alertmanager tar xzf -
    }
    
    Write-Info "Data restored. Restarting services..."
    Restart-Services
}

function Show-Help {
    @"

AIOps Monitoring Stack Deployment Script (PowerShell)
====================================================

Usage: .\deploy.ps1 -Command <COMMAND> [-Service <SERVICE>] [-BackupDir <DIR>]

Commands:
    install     Install and start the monitoring stack
    start       Start the monitoring stack
    stop        Stop the monitoring stack
    restart     Restart the monitoring stack
    status      Check service status
    logs        View logs (use -Service to specify service name)
    reload      Reload Prometheus configuration
    backup      Backup monitoring data
    restore     Restore monitoring data (use -BackupDir to specify backup directory)
    help        Show this help message

Examples:
    .\deploy.ps1 -Command install
    .\deploy.ps1 -Command start
    .\deploy.ps1 -Command logs -Service prometheus
    .\deploy.ps1 -Command backup
    .\deploy.ps1 -Command restore -BackupDir backups\20240101_120000

"@
}

# Main script logic
switch ($Command) {
    "install" {
        Test-Prerequisites
        New-EnvFile
        New-Directories
        New-CaddyConfig
        Start-Services
        Write-Info "Monitoring stack installed and started successfully!"
        Write-Info "Access Grafana at: http://localhost:3001"
        Write-Info "Access Prometheus at: http://localhost:9090"
        Write-Info "Access Alertmanager at: http://localhost:9093"
    }
    "start" {
        Start-Services
    }
    "stop" {
        Stop-Services
    }
    "restart" {
        Restart-Services
    }
    "status" {
        Get-ServiceStatus
    }
    "logs" {
        Show-Logs
    }
    "reload" {
        Reload-Prometheus
    }
    "backup" {
        Backup-Data
    }
    "restore" {
        Restore-Data
    }
    "help" {
        Show-Help
    }
    default {
        Write-Error "Unknown command: $Command"
        Show-Help
        exit 1
    }
}

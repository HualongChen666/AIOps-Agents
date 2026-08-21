#!/bin/bash
# AIOps Monitoring Stack Deployment Script
# =========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_info "Prerequisites check passed."
}

create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_info "Creating .env file with default values..."
        cat > "$ENV_FILE" << EOF
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
EOF
        print_warning "Please edit $ENV_FILE with your actual configuration values."
    else
        print_info ".env file already exists."
    fi
}

create_directories() {
    print_info "Creating necessary directories..."
    
    mkdir -p "${SCRIPT_DIR}/prometheus/alerts"
    mkdir -p "${SCRIPT_DIR}/grafana/provisioning/datasources"
    mkdir -p "${SCRIPT_DIR}/grafana/provisioning/dashboards"
    mkdir -p "${SCRIPT_DIR}/grafana/dashboards"
    mkdir -p "${SCRIPT_DIR}/alertmanager"
    mkdir -p "${SCRIPT_DIR}/caddy"
    
    print_info "Directories created."
}

create_caddy_config() {
    if [ ! -f "${SCRIPT_DIR}/caddy/Caddyfile" ]; then
        print_info "Creating Caddy configuration..."
        cat > "${SCRIPT_DIR}/caddy/Caddyfile" << EOF
{
    email admin@aiops.local
}

:80 {
    reverse_proxy prometheus:9090
    reverse_proxy grafana:3000
    reverse_proxy alertmanager:9093
}
EOF
        print_info "Caddy configuration created."
    else
        print_info "Caddy configuration already exists."
    fi
}

start_services() {
    print_info "Starting monitoring stack..."
    
    if docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" up -d
    else
        docker-compose -f "$COMPOSE_FILE" up -d
    fi
    
    print_info "Monitoring stack started."
}

stop_services() {
    print_info "Stopping monitoring stack..."
    
    if docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" down
    else
        docker-compose -f "$COMPOSE_FILE" down
    fi
    
    print_info "Monitoring stack stopped."
}

restart_services() {
    print_info "Restarting monitoring stack..."
    
    if docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" restart
    else
        docker-compose -f "$COMPOSE_FILE" restart
    fi
    
    print_info "Monitoring stack restarted."
}

check_services() {
    print_info "Checking service status..."
    
    if docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" ps
    else
        docker-compose -f "$COMPOSE_FILE" ps
    fi
}

view_logs() {
    local service=$1
    
    if [ -z "$service" ]; then
        print_info "Showing logs for all services..."
        if docker compose version &> /dev/null; then
            docker compose -f "$COMPOSE_FILE" logs -f
        else
            docker-compose -f "$COMPOSE_FILE" logs -f
        fi
    else
        print_info "Showing logs for $service..."
        if docker compose version &> /dev/null; then
            docker compose -f "$COMPOSE_FILE" logs -f "$service"
        else
            docker-compose -f "$COMPOSE_FILE" logs -f "$service"
        fi
    fi
}

reload_prometheus() {
    print_info "Reloading Prometheus configuration..."
    
    curl -X POST http://localhost:9090/-/reload
    
    print_info "Prometheus configuration reloaded."
}

backup_data() {
    local backup_dir="${SCRIPT_DIR}/backups/$(date +%Y%m%d_%H%M%S)"
    
    print_info "Creating backup at $backup_dir..."
    
    mkdir -p "$backup_dir"
    
    # Backup Prometheus data
    if docker ps | grep -q aiops-prometheus; then
        docker exec aiops-prometheus tar czf - /prometheus > "$backup_dir/prometheus-data.tar.gz"
    fi
    
    # Backup Grafana data
    if docker ps | grep -q aiops-grafana; then
        docker exec aiops-grafana tar czf - /var/lib/grafana > "$backup_dir/grafana-data.tar.gz"
    fi
    
    # Backup Alertmanager data
    if docker ps | grep -q aiops-alertmanager; then
        docker exec aiops-alertmanager tar czf - /alertmanager > "$backup_dir/alertmanager-data.tar.gz"
    fi
    
    print_info "Backup completed."
}

restore_data() {
    local backup_dir=$1
    
    if [ -z "$backup_dir" ]; then
        print_error "Please specify backup directory."
        exit 1
    fi
    
    if [ ! -d "$backup_dir" ]; then
        print_error "Backup directory does not exist: $backup_dir"
        exit 1
    fi
    
    print_info "Restoring data from $backup_dir..."
    
    # Restore Prometheus data
    if [ -f "$backup_dir/prometheus-data.tar.gz" ]; then
        docker exec -i aiops-prometheus tar xzf - < "$backup_dir/prometheus-data.tar.gz"
    fi
    
    # Restore Grafana data
    if [ -f "$backup_dir/grafana-data.tar.gz" ]; then
        docker exec -i aiops-grafana tar xzf - < "$backup_dir/grafana-data.tar.gz"
    fi
    
    # Restore Alertmanager data
    if [ -f "$backup_dir/alertmanager-data.tar.gz" ]; then
        docker exec -i aiops-alertmanager tar xzf - < "$backup_dir/alertmanager-data.tar.gz"
    fi
    
    print_info "Data restored. Restarting services..."
    restart_services
}

show_help() {
    cat << EOF
AIOps Monitoring Stack Deployment Script
=========================================

Usage: $0 [COMMAND]

Commands:
    install     Install and start the monitoring stack
    start       Start the monitoring stack
    stop        Stop the monitoring stack
    restart     Restart the monitoring stack
    status      Check service status
    logs        View logs (optional: specify service name)
    reload      Reload Prometheus configuration
    backup      Backup monitoring data
    restore     Restore monitoring data (specify backup directory)
    help        Show this help message

Examples:
    $0 install
    $0 start
    $0 logs prometheus
    $0 backup
    $0 restore backups/20240101_120000

EOF
}

# Main script logic
case "${1:-help}" in
    install)
        check_prerequisites
        create_env_file
        create_directories
        create_caddy_config
        start_services
        print_info "Monitoring stack installed and started successfully!"
        print_info "Access Grafana at: http://localhost:3001"
        print_info "Access Prometheus at: http://localhost:9090"
        print_info "Access Alertmanager at: http://localhost:9093"
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_services
        ;;
    logs)
        view_logs "$2"
        ;;
    reload)
        reload_prometheus
        ;;
    backup)
        backup_data
        ;;
    restore)
        restore_data "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

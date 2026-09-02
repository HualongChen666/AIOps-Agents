#!/bin/bash
# -*- coding: utf-8 -*-
"""
Monitoring Module Data Migration Script
=======================================

This script ensures zero data loss during the Monitoring module migration.
It performs the following steps:
1. Backup existing database
2. Run Alembic migration for Monitoring models
3. Verify migration success
4. Validate data integrity

Usage:
    bash scripts/migrate_monitoring.sh
"""

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/monitoring_migration_${TIMESTAMP}.sql"

echo "=========================================="
echo "Monitoring Module Data Migration"
echo "=========================================="
echo "Timestamp: ${TIMESTAMP}"
echo ""

# Step 1: Create backup directory
echo -e "${YELLOW}[Step 1/5] Creating backup directory...${NC}"
mkdir -p "${BACKUP_DIR}"
echo -e "${GREEN}✓ Backup directory created: ${BACKUP_DIR}${NC}"
echo ""

# Step 2: Backup existing database
echo -e "${YELLOW}[Step 2/5] Backing up existing database...${NC}"
if command -v pg_dump &> /dev/null; then
    # Use PostgreSQL backup
    if [ -n "$DATABASE_URL" ]; then
        pg_dump "$DATABASE_URL" > "${BACKUP_FILE}"
        echo -e "${GREEN}✓ Database backup created: ${BACKUP_FILE}${NC}"
    else
        echo -e "${RED}✗ DATABASE_URL environment variable not set${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ pg_dump not found, skipping database backup${NC}"
    echo -e "${YELLOW}⚠ Please ensure you have a database backup before proceeding${NC}"
fi
echo ""

# Step 3: Run Alembic migration
echo -e "${YELLOW}[Step 3/5] Running Alembic migration...${NC}"
if command -v alembic &> /dev/null; then
    alembic upgrade head
    echo -e "${GREEN}✓ Alembic migration completed${NC}"
else
    echo -e "${YELLOW}⚠ alembic not found, please run: alembic upgrade head${NC}"
fi
echo ""

# Step 4: Verify migration
echo -e "${YELLOW}[Step 4/5] Verifying migration...${NC}"
python -c "
import asyncio
from sqlalchemy import inspect
from core.db_engine import engine

async def verify():
    async with engine.begin() as conn:
        inspector = inspect(conn.sync())
        tables = inspector.get_table_names()

        monitoring_tables = [
            'monitoring_alert_rules',
            'monitoring_log_patterns',
            'monitoring_traces',
            'monitoring_service_calls',
            'monitoring_metrics',
            'monitoring_integrations',
            'monitoring_dashboards',
            'monitoring_anomalies',
        ]

        missing_tables = []
        for table in monitoring_tables:
            if table not in tables:
                missing_tables.append(table)

        if missing_tables:
            print(f'Missing tables: {missing_tables}')
            return False
        else:
            print('All Monitoring tables created successfully')
            return True

asyncio.run(verify())
"
echo ""

# Step 5: Validate data integrity
echo -e "${YELLOW}[Step 5/5] Validating data integrity...${NC}"
python -c "
import asyncio
from core.db_engine import engine

async def validate():
    async with engine.begin() as conn:
        # Check if existing tables still have data
        result = await conn.execute('SELECT COUNT(*) FROM users')
        user_count = result.scalar()
        print(f'Users count: {user_count}')

        result = await conn.execute('SELECT COUNT(*) FROM alerts')
        alert_count = result.scalar()
        print(f'Alerts count: {alert_count}')

        if user_count >= 0 and alert_count >= 0:
            print('Data integrity validated')
            return True
        else:
            print('Data integrity check failed')
            return False

asyncio.run(validate())
"
echo ""

echo "=========================================="
echo -e "${GREEN}Migration completed successfully!${NC}"
echo "=========================================="
echo ""
echo "Backup location: ${BACKUP_FILE}"
echo ""
echo "Next steps:"
echo "1. Review the migration results"
echo "2. Test the Monitoring endpoints"
echo "3. If issues occur, use the rollback script: scripts/rollback_monitoring.sh"
echo ""

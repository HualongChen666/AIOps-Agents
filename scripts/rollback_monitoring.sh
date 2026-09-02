#!/bin/bash
# -*- coding: utf-8 -*-
"""
Monitoring Module Rollback Script
=================================

This script rolls back the Monitoring module migration to ensure
zero data loss in case of issues.

Usage:
    bash scripts/rollback_monitoring.sh
"""

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"

echo "=========================================="
echo "Monitoring Module Rollback"
echo "=========================================="
echo ""

# Step 1: Check for backup files
echo -e "${YELLOW}[Step 1/3] Checking for backup files...${NC}"
if [ -d "${BACKUP_DIR}" ]; then
    BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/*.sql 2>/dev/null | wc -l)
    if [ "${BACKUP_COUNT}" -gt 0 ]; then
        echo -e "${GREEN}✓ Found ${BACKUP_COUNT} backup file(s)${NC}"
        LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.sql 2>/dev/null | head -1)
        echo "Latest backup: ${LATEST_BACKUP}"
    else
        echo -e "${RED}✗ No backup files found in ${BACKUP_DIR}${NC}"
        echo -e "${YELLOW}⚠ Proceeding with Alembic rollback only${NC}"
        LATEST_BACKUP=""
    fi
else
    echo -e "${YELLOW}⚠ Backup directory not found: ${BACKUP_DIR}${NC}"
    echo -e "${YELLOW}⚠ Proceeding with Alembic rollback only${NC}"
    LATEST_BACKUP=""
fi
echo ""

# Step 2: Rollback Alembic migration
echo -e "${YELLOW}[Step 2/3] Rolling back Alembic migration...${NC}"
if command -v alembic &> /dev/null; then
    # Rollback to previous version (021)
    alembic downgrade 021
    echo -e "${GREEN}✓ Alembic rollback completed${NC}"
else
    echo -e "${YELLOW}⚠ alembic not found, please run: alembic downgrade 021${NC}"
fi
echo ""

# Step 3: Restore database from backup (if available)
if [ -n "${LATEST_BACKUP}" ]; then
    echo -e "${YELLOW}[Step 3/3] Restoring database from backup...${NC}"
    if command -v psql &> /dev/null; then
        if [ -n "$DATABASE_URL" ]; then
            psql "$DATABASE_URL" < "${LATEST_BACKUP}"
            echo -e "${GREEN}✓ Database restored from: ${LATEST_BACKUP}${NC}"
        else
            echo -e "${RED}✗ DATABASE_URL environment variable not set${NC}"
            echo -e "${YELLOW}⚠ Please restore manually: psql \$DATABASE_URL < ${LATEST_BACKUP}${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ psql not found, please restore manually: psql \$DATABASE_URL < ${LATEST_BACKUP}${NC}"
    fi
else
    echo -e "${YELLOW}[Step 3/3] Skipping database restore (no backup available)${NC}"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}Rollback completed!${NC}"
echo "=========================================="
echo ""
echo "The Monitoring module has been rolled back to the previous state."
echo ""
echo "Next steps:"
echo "1. Verify the system is working correctly"
echo "2. Review the rollback logs"
echo "3. If needed, re-run the migration after fixing any issues"
echo ""

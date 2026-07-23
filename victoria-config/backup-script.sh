#!/bin/bash
# VictoriaMetrics Backup Script
# This script creates snapshots of VictoriaMetrics data for backup

set -e

# Configuration
VM_CONTAINER_NAME="victoriametrics"
BACKUP_DIR="./backups/victoriametrics"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="victoria_backup_${TIMESTAMP}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "Starting VictoriaMetrics backup at ${TIMESTAMP}"

# Create snapshot using VictoriaMetrics snapshot API
echo "Creating snapshot..."
docker exec "${VM_CONTAINER_NAME}" \
    vmctl snapshot create \
    --snapshot-path="/tmp/${BACKUP_NAME}" || {
    echo "Failed to create snapshot"
    exit 1
}

# Copy snapshot from container to host
echo "Copying snapshot to host..."
docker cp "${VM_CONTAINER_NAME}:/tmp/${BACKUP_NAME}" "${BACKUP_DIR}/" || {
    echo "Failed to copy snapshot"
    exit 1
}

# Clean up snapshot from container
echo "Cleaning up snapshot from container..."
docker exec "${VM_CONTAINER_NAME}" rm -rf "/tmp/${BACKUP_NAME}" || true

# Compress backup
echo "Compressing backup..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"
cd -

echo "Backup completed: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

# Clean up old backups (older than RETENTION_DAYS)
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -name "victoria_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# Optional: Upload to S3 or other cloud storage
# AWS S3 upload example (requires awscli)
# if command -v aws &> /dev/null; then
#     echo "Uploading backup to S3..."
#     aws s3 cp "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" \
#         "s3://your-bucket/victoriametrics-backups/${BACKUP_NAME}.tar.gz"
# fi

echo "Backup process completed successfully"

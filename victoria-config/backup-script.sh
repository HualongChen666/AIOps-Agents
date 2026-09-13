#!/bin/bash
# VictoriaMetrics Backup Script
# Creates a consistent snapshot via the VictoriaMetrics snapshot HTTP API, copies
# it out of the container, compresses it and prunes old backups.

set -euo pipefail

# Configuration (override via environment)
VM_CONTAINER_NAME="${VM_CONTAINER_NAME:-aiops-victoria-metrics}"
VM_HTTP_ADDR="${VM_HTTP_ADDR:-http://localhost:8428}"
VM_STORAGE_PATH="${VM_STORAGE_PATH:-/victoria-metrics-data}"
BACKUP_DIR="${BACKUP_DIR:-./backups/victoriametrics}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"

echo "Starting VictoriaMetrics backup at $(date +%Y%m%d_%H%M%S)"

# Create snapshot using the VictoriaMetrics snapshot API
# (https://docs.victoriametrics.com/#how-to-work-with-snapshots)
echo "Creating snapshot via ${VM_HTTP_ADDR}/snapshot/create ..."
if ! RESPONSE=$(curl -fsS -X POST "${VM_HTTP_ADDR}/snapshot/create"); then
    echo "Failed to create snapshot (is VictoriaMetrics reachable at ${VM_HTTP_ADDR}?)"
    exit 1
fi

SNAPSHOT_NAME=$(printf '%s' "${RESPONSE}" | sed -n 's/.*"snapshot":"\([^"]*\)".*/\1/p')
if [ -z "${SNAPSHOT_NAME}" ]; then
    echo "Could not parse snapshot name from response: ${RESPONSE}"
    exit 1
fi
echo "Snapshot created: ${SNAPSHOT_NAME}"

# Copy the snapshot directory out of the container
echo "Copying snapshot to host..."
docker cp "${VM_CONTAINER_NAME}:${VM_STORAGE_PATH}/snapshots/${SNAPSHOT_NAME}" "${BACKUP_DIR}/" || {
    echo "Failed to copy snapshot"
    exit 1
}

# Remove the snapshot inside the container to free disk space
echo "Deleting snapshot inside container..."
curl -fsS "${VM_HTTP_ADDR}/snapshot/delete?snapshot=${SNAPSHOT_NAME}" || true

# Compress the backup
echo "Compressing backup..."
tar -czf "${BACKUP_DIR}/victoria_backup_${SNAPSHOT_NAME}.tar.gz" \
    -C "${BACKUP_DIR}" "${SNAPSHOT_NAME}"
rm -rf "${BACKUP_DIR:?}/${SNAPSHOT_NAME}"

echo "Backup completed: ${BACKUP_DIR}/victoria_backup_${SNAPSHOT_NAME}.tar.gz"

# Clean up old backups
echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "victoria_backup_*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete

# Optional: Upload to S3 or other cloud storage
# if command -v aws >/dev/null 2>&1; then
#     aws s3 cp "${BACKUP_DIR}/victoria_backup_${SNAPSHOT_NAME}.tar.gz" \
#         "s3://${BACKUP_BUCKET}/victoriametrics-backups/"
# fi

echo "Backup process completed successfully"

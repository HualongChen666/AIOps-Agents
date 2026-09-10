# 示例：Restore backup
curl -X POST "http://localhost:8000/api/v1/backup/restore" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

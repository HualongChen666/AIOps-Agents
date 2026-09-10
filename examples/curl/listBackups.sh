# 示例：List backups
curl -X GET "http://localhost:8000/api/v1/backup/list" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

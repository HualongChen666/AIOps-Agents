# 示例：Create backup
curl -X POST "http://localhost:8000/api/v1/backup/create" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

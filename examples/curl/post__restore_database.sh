# 示例：POST /restore/database
curl -X POST "http://localhost:8000/api/v1/restore/database" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

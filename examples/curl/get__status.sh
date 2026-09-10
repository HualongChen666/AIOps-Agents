# 示例：GET /status
curl -X GET "http://localhost:8000/api/v1/status" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

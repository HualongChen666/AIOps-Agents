# 示例：Health check
curl -X GET "http://localhost:8000/api/v1/health" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

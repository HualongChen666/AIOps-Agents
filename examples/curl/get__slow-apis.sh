# 示例：GET /slow-apis
curl -X GET "http://localhost:8000/api/v1/slow-apis" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

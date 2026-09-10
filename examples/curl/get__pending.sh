# 示例：GET /pending
curl -X GET "http://localhost:8000/api/v1/pending" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

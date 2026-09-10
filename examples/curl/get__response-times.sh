# 示例：GET /response-times
curl -X GET "http://localhost:8000/api/v1/response-times" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

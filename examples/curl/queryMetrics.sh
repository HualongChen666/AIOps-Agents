# 示例：Query metrics
curl -X GET "http://localhost:8000/api/v1/metrics" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

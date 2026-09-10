# 示例：List alerts
curl -X GET "http://localhost:8000/api/v1/alerts" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

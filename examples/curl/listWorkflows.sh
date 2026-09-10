# 示例：List workflows
curl -X GET "http://localhost:8000/api/v1/workflows" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

# 示例：Execute auto-heal
curl -X POST "http://localhost:8000/api/v1/autoheal/execute" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

# 示例：POST /metrics/reset
curl -X POST "http://localhost:8000/api/v1/metrics/reset" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

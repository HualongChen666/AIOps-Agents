# 示例：List anomalies
curl -X GET "http://localhost:8000/api/v1/anomalies" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

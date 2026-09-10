# 示例：Delete anomaly
ANOMALY_ID="${ANOMALY_ID:-YOUR_ANOMALY_ID}"
curl -X DELETE "http://localhost:8000/api/v1/anomalies/${ANOMALY_ID}" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

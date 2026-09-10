# 示例：Get anomaly
ANOMALY_ID="${ANOMALY_ID:-YOUR_ANOMALY_ID}"
curl -X GET "http://localhost:8000/api/v1/anomalies/${ANOMALY_ID}" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

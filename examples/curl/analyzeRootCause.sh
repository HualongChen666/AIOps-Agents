# 示例：Analyze root cause
ANOMALY_ID="${ANOMALY_ID:-YOUR_ANOMALY_ID}"
curl -X POST "http://localhost:8000/api/v1/anomalies/${ANOMALY_ID}/root-cause" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

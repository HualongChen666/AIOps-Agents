# 示例：PATCH /{alert_id}
ALERT_ID="${ALERT_ID:-YOUR_ALERT_ID}"
curl -X PATCH "http://localhost:8000/api/v1/${ALERT_ID}" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

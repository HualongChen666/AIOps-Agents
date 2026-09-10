# 示例：GET /conversation/{conversation_id}
CONVERSATION_ID="${CONVERSATION_ID:-YOUR_CONVERSATION_ID}"
curl -X GET "http://localhost:8000/api/v1/conversation/${CONVERSATION_ID}" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

# 示例：Get workflow
WORKFLOW_ID="${WORKFLOW_ID:-YOUR_WORKFLOW_ID}"
curl -X GET "http://localhost:8000/api/v1/workflows/${WORKFLOW_ID}" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

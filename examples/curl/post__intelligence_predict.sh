# 示例：POST /intelligence/predict
curl -X POST "http://localhost:8000/api/v1/intelligence/predict" \
    -H "Authorization: Bearer ${AIOPS_TOKEN:-YOUR_TOKEN}"

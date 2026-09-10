# -*- coding: utf-8 -*-
import requests

YOUR_WORKFLOW_ID = ""
workflow_id = "YOUR_WORKFLOW_ID"

# 示例：Get workflow
# 使用 GET 方法请求 /workflows/{workflow_id}
url = f"http://localhost:8000/api/v1/workflows/{workflow_id}"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

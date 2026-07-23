# -*- coding: utf-8 -*-
YOUR_WORKFLOW_ID = ""
workflow_id = "YOUR_WORKFLOW_ID"
import requests

# 示例：Get workflow
# 使用 GET 方法请求 /workflows/{workflow_id}
url = f"http://localhost:8080/api/v1/workflows/{workflow_id}"
try:
    response = requests.get(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

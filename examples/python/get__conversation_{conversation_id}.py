# -*- coding: utf-8 -*-
import requests

YOUR_CONVERSATION_ID = ""
conversation_id = "YOUR_CONVERSATION_ID"

# 示例：GET /conversation/{conversation_id}
# 使用 GET 方法请求 /conversation/{conversation_id}
url = f"http://localhost:8000/api/v1/conversation/{conversation_id}"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

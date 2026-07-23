# -*- coding: utf-8 -*-
YOUR_CONVERSATION_ID = ""
conversation_id = "YOUR_CONVERSATION_ID"
import requests

# 示例：GET /conversation/{conversation_id}
# 使用 GET 方法请求 /conversation/{conversation_id}
url = f"http://localhost:8080/api/v1/conversation/{conversation_id}"
try:
    response = requests.get(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

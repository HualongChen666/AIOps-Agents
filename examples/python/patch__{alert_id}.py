# -*- coding: utf-8 -*-
import requests

YOUR_ALERT_ID = ""
alert_id = "YOUR_ALERT_ID"

# 示例：PATCH /{alert_id}
# 使用 PATCH 方法请求 /{alert_id}
url = f"http://localhost:8000/api/v1/{alert_id}"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.patch(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

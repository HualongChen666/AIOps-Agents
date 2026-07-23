# -*- coding: utf-8 -*-
YOUR_ALERT_ID = ""
alert_id = "YOUR_ALERT_ID"
import requests

# 示例：PATCH /{alert_id}
# 使用 PATCH 方法请求 /{alert_id}
url = f"http://localhost:8080/api/v1/{alert_id}"
try:
    response = requests.patch(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

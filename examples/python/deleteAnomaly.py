# -*- coding: utf-8 -*-
import requests

YOUR_ANOMALY_ID = ""
anomaly_id = "YOUR_ANOMALY_ID"

# 示例：Delete anomaly
# 使用 DELETE 方法请求 /anomalies/{anomaly_id}
url = f"http://localhost:8000/api/v1/anomalies/{anomaly_id}"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.delete(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

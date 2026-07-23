# -*- coding: utf-8 -*-
YOUR_ANOMALY_ID = ""
anomaly_id = "YOUR_ANOMALY_ID"
import requests

# 示例：Update anomaly
# 使用 PUT 方法请求 /anomalies/{anomaly_id}
url = f"http://localhost:8080/api/v1/anomalies/{anomaly_id}"
try:
    response = requests.put(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

# -*- coding: utf-8 -*-
import requests

YOUR_ANOMALY_ID = ""
anomaly_id = "YOUR_ANOMALY_ID"

# 示例：Get anomaly
# 使用 GET 方法请求 /anomalies/{anomaly_id}
url = f"http://localhost:8080/api/v1/anomalies/{anomaly_id}"
try:
    response = requests.get(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

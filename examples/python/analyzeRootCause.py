# -*- coding: utf-8 -*-
import requests

YOUR_ANOMALY_ID = ""
anomaly_id = "YOUR_ANOMALY_ID"

# 示例：Analyze root cause
# 使用 POST 方法请求 /anomalies/{anomaly_id}/root-cause
url = f"http://localhost:8080/api/v1/anomalies/{anomaly_id}/root-cause"
try:
    response = requests.post(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

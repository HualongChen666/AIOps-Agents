# -*- coding: utf-8 -*-
import requests

# 示例：POST /predict/anomalies
# 使用 POST 方法请求 /predict/anomalies
url = "http://localhost:8000/api/v1/predict/anomalies"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.post(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

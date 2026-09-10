# -*- coding: utf-8 -*-
import requests

# 示例：GET /intelligence/topology
# 使用 GET 方法请求 /intelligence/topology
url = "http://localhost:8000/api/v1/intelligence/topology"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

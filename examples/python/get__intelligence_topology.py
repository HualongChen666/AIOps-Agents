# -*- coding: utf-8 -*-
import requests

# 示例：GET /intelligence/topology
# 使用 GET 方法请求 /intelligence/topology
url = "http://localhost:8080/api/v1/intelligence/topology"
try:
    response = requests.get(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

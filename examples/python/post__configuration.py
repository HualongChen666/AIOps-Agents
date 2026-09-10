# -*- coding: utf-8 -*-
import requests

# 示例：POST /configuration
# 使用 POST 方法请求 /configuration
url = "http://localhost:8000/api/v1/configuration"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.post(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

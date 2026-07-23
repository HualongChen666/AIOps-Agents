# -*- coding: utf-8 -*-
import requests

# 示例：POST /redis
# 使用 POST 方法请求 /redis
url = "http://localhost:8080/api/v1/redis"
try:
    response = requests.post(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

# -*- coding: utf-8 -*-
import requests

# 示例：Execute auto-heal
# 使用 POST 方法请求 /autoheal/execute
url = "http://localhost:8080/api/v1/autoheal/execute"
try:
    response = requests.post(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

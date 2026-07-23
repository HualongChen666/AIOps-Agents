# -*- coding: utf-8 -*-
import requests

# 示例：DELETE /
# 使用 DELETE 方法请求 /
url = "http://localhost:8080/api/v1/"
try:
    response = requests.delete(url)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

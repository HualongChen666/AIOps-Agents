# -*- coding: utf-8 -*-
import requests

# 示例：List backups
# 使用 GET 方法请求 /backup/list
url = "http://localhost:8000/api/v1/backup/list"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

try:
    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Request failed:", e)

# API 使用入门指南

## 1. 简介
本项目提供基于 **FastAPI** 的 AIOps 统一 API，涵盖告警、异常、容量、成本、自动修复、拓扑等核心能力。所有接口遵循 **OpenAPI 3.0** 规范，可通过自动生成的 Swagger UI（`/docs`）进行交互。

## 2. 认证方式
- **Bearer Token**（BearerAuth）是唯一受支持的认证方式。
- 在请求头中加入 `Authorization: Bearer <YOUR_TOKEN>` 即可访问受保护的接口。
- 示例（Python）:
```python
import requests
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "YOUR_TOKEN"
headers = {"Authorization": f"Bearer {TOKEN}"}
resp = requests.get(f"{BASE_URL}/health", headers=headers)
print(resp.json())
```
- 示例（curl）:
```bash
curl -X GET http://localhost:8000/api/v1/health \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 3. 常用请求 / 响应格式
所有成功请求返回 **application/json**，示例结构已在 OpenAPI 文档中提供（`example`字段）。错误响应统一使用以下格式：
```json
{
  "error": "string",
  "message": "string",
  "detail": null
}
```
对应 HTTP 状态码：
- **400** – 参数错误
- **401** – 未授权（缺少或无效 token）
- **403** – 权限不足
- **404** – 资源未找到
- **500** – 服务器内部错误

## 4. 示例 API
下面列出常用核心 API（已在 `examples/` 目录提供完整示例代码），并给出简要说明。

| 方法 | 路径 | 功能 | 示例代码 |
|------|------|------|----------|
| `GET` | `/health` | 检查服务健康状态 | [Python 示例](../examples/python/health_check.py) |
| `GET` | `/anomalies` | 列出所有异常事件 | [Python 示例](../examples/python/listAnomalies.py) |
| `POST` | `/anomalies` | 创建新异常 | [Python 示例](../examples/python/createAnomaly.py) |
| `GET` | `/alerts` | 获取告警列表 | [Python 示例](../examples/python/listAlerts.py) |
| `POST` | `/autoheal/execute` | 触发自动修复 | [Python 示例](../examples/python/executeAutoHeal.py) |
| `GET` | `/capacity/forecast` | 查询容量预测 | [Python 示例](../examples/python/getCapacityForecast.py) |
| `GET` | `/cost/forecast` | 查询成本预测 | [Python 示例](../examples/python/getCostForecast.py) |
| `GET` | `/topology` | 获取系统拓扑结构 | [Python 示例](../examples/python/getTopology.py) |

> 详细的请求/响应字段说明请参阅生成的 OpenAPI 文档（`openapi.yaml`）以及对应的 **example** 部分。

## 5. 错误处理与重试
- 对于 **5xx** 错误，建议使用指数退避（exponential backoff）重试。
- 对于 **4xx** 错误，请检查请求参数、认证 token 或权限。
- 所有异常均返回统一错误结构（见上表），便于前端统一处理。

## 6. 代码示例
项目根目录下的 `examples/` 包含可直接运行的示例，使用方式：
```bash
# 进入示例目录
cd examples/python
# 运行示例（请自行替换 BASE_URL 与 TOKEN）
python listAnomalies.py
```
示例代码已包含完整的请求、响应解析与异常捕获，适合作为开发者快速入门的参考。

## 7. 进一步阅读
- 完整 OpenAPI 规范文件：`openapi.yaml`（或 `openapi.json`）
- Swagger UI 地址：`http://<host>:<port>/docs`
- 项目源码位于 `api/` 包下，可直接查看路由实现细节。

---
*本文档遵循项目文档约定，保持 Markdown 结构一致，已在 `docs/api/` 目录创建。*
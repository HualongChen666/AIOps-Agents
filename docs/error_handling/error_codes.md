# 错误码体系设计文档

## 1. 概述

本文档定义了AIOps Agent系统的统一错误码体系，包含编码规则、模块定义、错误码列表和国际化支持。

## 2. 错误码编码规则

### 2.1 格式定义

**格式**: `MM_TT_NNNN`

- **MM**: 模块码（2位数字，01-20）
- **TT**: 错误类型码（2位数字，01-16）
- **NNNN**: 序号（4位数字，0001-9999）

### 2.2 示例

- `01_01_0001`: 通用模块的验证错误，序号0001
- `09_06_0001`: 数据库模块的连接错误，序号0001
- `11_12_0001`: AI引擎模块的模型错误，序号0001

## 3. 模块码定义

| 模块码 | 模块名称 | 英文标识 | 描述 |
|--------|---------|---------|------|
| 01 | 通用 | GEN | 通用错误 |
| 02 | 认证授权 | AUTH | 认证授权相关 |
| 03 | 用户管理 | USER | 用户管理相关 |
| 04 | 告警管理 | ALERT | 告警管理相关 |
| 05 | 修复管理 | REPAIR | 修复管理相关 |
| 06 | 拓扑管理 | TOPO | 拓扑管理相关 |
| 07 | 工作流管理 | WORKFLOW | 工作流相关 |
| 08 | 审计管理 | AUDIT | 审计相关 |
| 09 | 数据库 | DB | 数据库相关 |
| 10 | 缓存 | CACHE | 缓存相关 |
| 11 | AI引擎 | AI | AI引擎相关 |
| 12 | RAG系统 | RAG | RAG系统相关 |
| 13 | 代理编排 | AGENT | 代理编排相关 |
| 14 | 监控 | MONITOR | 监控相关 |
| 15 | 外部服务 | EXT | 外部服务相关 |
| 16 | 配置 | CONFIG | 配置相关 |
| 17 | 网络 | NET | 网络相关 |
| 18 | 资源 | RESOURCE | 资源相关 |
| 19 | 集成 | INTEGRATION | 集成相关 |
| 20 | 系统 | SYSTEM | 系统相关 |

## 4. 错误类型码定义

| 类型码 | 类型名称 | 英文标识 | 描述 |
|--------|---------|---------|------|
| 01 | 验证错误 | VALIDATION | 输入验证失败 |
| 02 | 未找到 | NOT_FOUND | 资源未找到 |
| 03 | 权限错误 | PERMISSION | 权限相关错误 |
| 04 | 业务逻辑 | BUSINESS | 业务逻辑错误 |
| 05 | 状态错误 | STATE | 状态相关错误 |
| 06 | 连接错误 | CONNECTION | 连接相关错误 |
| 07 | 查询错误 | QUERY | 查询相关错误 |
| 08 | 约束错误 | CONSTRAINT | 约束相关错误 |
| 09 | 超时错误 | TIMEOUT | 超时相关错误 |
| 10 | 限流错误 | RATE_LIMIT | 限流相关错误 |
| 11 | 服务错误 | SERVICE | 服务相关错误 |
| 12 | 模型错误 | MODEL | 模型相关错误 |
| 13 | 数据错误 | DATA | 数据相关错误 |
| 14 | 配置错误 | CONFIG | 配置相关错误 |
| 15 | 系统错误 | SYSTEM | 系统相关错误 |
| 16 | 未知错误 | UNKNOWN | 未知错误 |

## 5. 错误码详细列表

### 5.1 通用错误 (01_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 01_01_0001 | GEN_VALIDATION_FAILED | 通用参数验证失败 | 400 | WARNING |
| 01_01_0002 | GEN_INVALID_FORMAT | 通用参数格式错误 | 400 | WARNING |
| 01_01_0003 | GEN_MISSING_PARAMETER | 通用参数缺失 | 400 | WARNING |
| 01_01_0004 | GEN_INVALID_TYPE | 通用参数类型错误 | 400 | WARNING |
| 01_01_0005 | GEN_INVALID_RANGE | 通用参数范围错误 | 400 | WARNING |
| 01_02_0001 | GEN_RESOURCE_NOT_FOUND | 通用资源未找到 | 404 | ERROR |
| 01_02_0002 | GEN_ENDPOINT_NOT_FOUND | 通用接口不存在 | 404 | ERROR |
| 01_02_0003 | GEN_FILE_NOT_FOUND | 通用文件未找到 | 404 | ERROR |
| 01_03_0001 | GEN_PERMISSION_DENIED | 通用权限不足 | 403 | ERROR |
| 01_03_0002 | GEN_ROLE_INSUFFICIENT | 通用角色权限不足 | 403 | ERROR |
| 01_03_0003 | GEN_ACCESS_DENIED | 通用访问被拒绝 | 403 | ERROR |
| 01_04_0001 | GEN_BUSINESS_ERROR | 通用业务逻辑错误 | 422 | ERROR |
| 01_04_0002 | GEN_OPERATION_FAILED | 通用操作失败 | 422 | ERROR |
| 01_05_0001 | GEN_INVALID_STATE | 通用状态无效 | 422 | ERROR |
| 01_05_0002 | GEN_STATE_TRANSITION_ERROR | 通用状态转换错误 | 422 | ERROR |
| 01_09_0001 | GEN_REQUEST_TIMEOUT | 通用请求超时 | 408 | ERROR |
| 01_09_0002 | GEN_OPERATION_TIMEOUT | 通用操作超时 | 408 | ERROR |
| 01_10_0001 | GEN_RATE_LIMIT_EXCEEDED | 通用请求限流 | 429 | WARNING |
| 01_10_0002 | GEN_FREQUENCY_LIMIT | 通用频率限制 | 429 | WARNING |
| 01_15_0001 | GEN_INTERNAL_ERROR | 通用内部错误 | 500 | ERROR |
| 01_15_0002 | GEN_SERVICE_UNAVAILABLE | 通用服务不可用 | 503 | ERROR |
| 01_15_0003 | GEN_UNEXPECTED_ERROR | 通用未知错误 | 500 | ERROR |

### 5.2 认证授权错误 (02_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 02_01_0001 | AUTH_INVALID_CREDENTIALS | 用户名或密码错误 | 401 | WARNING |
| 02_01_0002 | AUTH_INVALID_TOKEN | Token格式错误 | 401 | WARNING |
| 02_01_0003 | AUTH_TOKEN_EXPIRED | Token已过期 | 401 | WARNING |
| 02_01_0004 | AUTH_TOKEN_REVOKED | Token已撤销 | 401 | WARNING |
| 02_01_0005 | AUTH_INVALID_SIGNATURE | Token签名无效 | 401 | WARNING |
| 02_03_0001 | AUTH_PERMISSION_DENIED | 权限不足 | 403 | ERROR |
| 02_03_0002 | AUTH_ROLE_INSUFFICIENT | 角色权限不足 | 403 | ERROR |
| 02_03_0003 | AUTH_RESOURCE_ACCESS_DENIED | 资源访问被拒绝 | 403 | ERROR |
| 02_03_0004 | AUTH_OPERATION_NOT_ALLOWED | 操作不允许 | 403 | ERROR |
| 02_09_0001 | AUTH_SERVICE_TIMEOUT | 认证服务超时 | 408 | ERROR |
| 02_09_0002 | AUTHORIZATION_TIMEOUT | 授权服务超时 | 408 | ERROR |
| 02_11_0001 | AUTH_SERVICE_UNAVAILABLE | 认证服务不可用 | 503 | ERROR |
| 02_11_0002 | AUTH_PROVIDER_ERROR | 认证提供者错误 | 503 | ERROR |

### 5.3 数据库错误 (09_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 09_06_0001 | DB_CONNECTION_FAILED | 数据库连接失败 | 500 | ERROR |
| 09_06_0002 | DB_CONNECTION_POOL_EXHAUSTED | 数据库连接池耗尽 | 500 | ERROR |
| 09_06_0003 | DB_CONNECTION_TIMEOUT | 数据库连接超时 | 500 | ERROR |
| 09_06_0004 | DB_CONNECTION_LOST | 数据库连接丢失 | 500 | ERROR |
| 09_07_0001 | DB_QUERY_ERROR | SQL查询错误 | 500 | ERROR |
| 09_07_0002 | DB_SYNTAX_ERROR | SQL语法错误 | 500 | ERROR |
| 09_07_0003 | DB_EXECUTION_ERROR | SQL执行错误 | 500 | ERROR |
| 09_08_0001 | DB_UNIQUE_CONSTRAINT | 唯一约束冲突 | 409 | ERROR |
| 09_08_0002 | DB_FOREIGN_KEY_CONSTRAINT | 外键约束冲突 | 409 | ERROR |
| 09_08_0003 | DB_NOT_NULL_CONSTRAINT | 非空约束冲突 | 409 | ERROR |
| 09_08_0004 | DB_CHECK_CONSTRAINT | 检查约束冲突 | 409 | ERROR |
| 09_09_0001 | DB_QUERY_TIMEOUT | 数据库查询超时 | 500 | ERROR |
| 09_09_0002 | DB_TRANSACTION_TIMEOUT | 数据库事务超时 | 500 | ERROR |
| 09_09_0003 | DB_LOCK_TIMEOUT | 数据库锁超时 | 500 | ERROR |
| 09_13_0001 | DB_DATA_CORRUPTION | 数据损坏 | 500 | FATAL |
| 09_13_0002 | DB_DATA_INCONSISTENCY | 数据不一致 | 500 | FATAL |
| 09_13_0003 | DB_INTEGRITY_ERROR | 数据完整性错误 | 500 | FATAL |
| 09_15_0001 | DB_SYSTEM_ERROR | 数据库系统错误 | 500 | ERROR |
| 09_15_0002 | DB_DISK_FULL | 数据库磁盘空间不足 | 500 | CRITICAL |

### 5.4 AI引擎错误 (11_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 11_06_0001 | AI_CONNECTION_FAILED | LLM连接失败 | 500 | ERROR |
| 11_06_0002 | AI_API_CONNECTION_ERROR | AI API连接错误 | 500 | ERROR |
| 11_09_0001 | AI_INFERENCE_TIMEOUT | LLM推理超时 | 500 | ERROR |
| 11_09_0002 | AI_REQUEST_TIMEOUT | AI请求超时 | 500 | ERROR |
| 11_12_0001 | AI_MODEL_LOAD_FAILED | 模型加载失败 | 500 | ERROR |
| 11_12_0002 | AI_MODEL_INFERENCE_ERROR | 模型推理错误 | 500 | ERROR |
| 11_12_0003 | AI_MODEL_NOT_FOUND | 模型未找到 | 404 | ERROR |
| 11_12_0004 | AI_MODEL_VERSION_ERROR | 模型版本错误 | 500 | ERROR |
| 11_10_0001 | AI_RATE_LIMIT_EXCEEDED | API调用限流 | 429 | WARNING |
| 11_10_0002 | AI_TOKEN_LIMIT_EXCEEDED | Token使用超限 | 429 | WARNING |
| 11_10_0003 | AI_QUOTA_EXCEEDED | 配额超限 | 429 | WARNING |
| 11_11_0001 | AI_SERVICE_UNAVAILABLE | AI服务不可用 | 503 | ERROR |
| 11_11_0002 | AI_API_ERROR | AI API错误 | 502 | ERROR |
| 11_13_0001 | AI_INVALID_INPUT | 输入数据错误 | 400 | WARNING |
| 11_13_0002 | AI_OUTPUT_PARSE_ERROR | 输出解析错误 | 500 | ERROR |
| 11_13_0003 | AI_INVALID_RESPONSE | 无效响应 | 500 | ERROR |
| 11_13_0004 | AI_RESPONSE_TOO_LARGE | 响应过大 | 500 | ERROR |

### 5.5 RAG系统错误 (12_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 12_06_0001 | RAG_VECTOR_DB_CONNECTION_FAILED | 向量数据库连接失败 | 500 | ERROR |
| 12_06_0002 | RAG_EMBEDDING_SERVICE_ERROR | 嵌入服务错误 | 500 | ERROR |
| 12_07_0001 | RAG_VECTOR_SEARCH_ERROR | 向量检索错误 | 500 | ERROR |
| 12_07_0002 | RAG_RETRIEVAL_ERROR | 检索错误 | 500 | ERROR |
| 12_09_0001 | RAG_VECTOR_SEARCH_TIMEOUT | 向量检索超时 | 500 | ERROR |
| 12_09_0002 | RAG_EMBEDDING_TIMEOUT | 嵌入超时 | 500 | ERROR |
| 12_13_0001 | RAG_DOCUMENT_PARSE_ERROR | 文档解析错误 | 500 | ERROR |
| 12_13_0002 | RAG_DOCUMENT_INDEX_ERROR | 文档索引错误 | 500 | ERROR |
| 12_13_0003 | RAG_CHUNK_ERROR | 文档分块错误 | 500 | ERROR |
| 12_11_0001 | RAG_SERVICE_UNAVAILABLE | RAG服务不可用 | 503 | ERROR |
| 12_11_0002 | RAG_PIPELINE_ERROR | RAG管道错误 | 500 | ERROR |

### 5.6 代理编排错误 (13_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 13_06_0001 | AGENT_CONNECTION_FAILED | 代理连接失败 | 500 | ERROR |
| 13_06_0002 | AGENT_COMMUNICATION_ERROR | 代理通信错误 | 500 | ERROR |
| 13_09_0001 | AGENT_EXECUTION_TIMEOUT | 代理执行超时 | 500 | ERROR |
| 13_09_0002 | AGENT_RESPONSE_TIMEOUT | 代理响应超时 | 500 | ERROR |
| 13_05_0001 | AGENT_INVALID_STATE | 代理状态错误 | 422 | ERROR |
| 13_05_0002 | AGENT_STATE_TRANSITION_ERROR | 代理状态转换错误 | 422 | ERROR |
| 13_11_0001 | AGENT_SERVICE_UNAVAILABLE | 代理服务不可用 | 503 | ERROR |
| 13_11_0002 | AGENT_ORCHESTRATION_ERROR | 代理编排错误 | 500 | ERROR |
| 13_04_0001 | WORKFLOW_EXECUTION_ERROR | 工作流执行错误 | 500 | ERROR |
| 13_04_0002 | WORKFLOW_STATE_ERROR | 工作流状态错误 | 422 | ERROR |
| 13_04_0003 | WORKFLOW_VALIDATION_ERROR | 工作流验证错误 | 400 | WARNING |

### 5.7 外部服务错误 (15_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 15_06_0001 | EXT_CONNECTION_FAILED | 外部服务连接失败 | 502 | ERROR |
| 15_06_0002 | EXT_NETWORK_ERROR | 外部服务网络错误 | 502 | ERROR |
| 15_09_0001 | EXT_SERVICE_TIMEOUT | 外部服务超时 | 504 | ERROR |
| 15_09_0002 | EXT_REQUEST_TIMEOUT | 外部请求超时 | 504 | ERROR |
| 15_11_0001 | EXT_SERVICE_UNAVAILABLE | 外部服务不可用 | 502 | ERROR |
| 15_11_0002 | EXT_SERVICE_ERROR | 外部服务错误 | 502 | ERROR |
| 15_13_0001 | EXT_INVALID_RESPONSE | 外部服务响应错误 | 502 | ERROR |
| 15_13_0002 | EXT_DATA_ERROR | 外部服务数据错误 | 502 | ERROR |
| 15_13_0003 | EXT_PARSE_ERROR | 外部服务解析错误 | 502 | ERROR |

### 5.8 系统错误 (20_XX_NNNN)

| 错误码 | 错误名称 | 描述 | HTTP状态码 | 严重程度 |
|--------|---------|------|-----------|---------|
| 20_06_0001 | SYSTEM_RESOURCE_INSUFFICIENT | 系统资源不足 | 503 | ERROR |
| 20_06_0002 | SYSTEM_MEMORY_INSUFFICIENT | 内存不足 | 503 | ERROR |
| 20_06_0003 | SYSTEM_DISK_INSUFFICIENT | 磁盘空间不足 | 503 | ERROR |
| 20_06_0004 | SYSTEM_CPU_HIGH | CPU使用率过高 | 503 | WARNING |
| 20_14_0001 | SYSTEM_CPU_USAGE_HIGH | CPU使用率过高 | 503 | WARNING |
| 20_14_0002 | SYSTEM_MEMORY_USAGE_HIGH | 内存使用率过高 | 503 | WARNING |
| 20_14_0003 | SYSTEM_DISK_USAGE_HIGH | 磁盘使用率过高 | 503 | WARNING |
| 20_15_0001 | SYSTEM_FATAL_ERROR | 系统致命错误 | 500 | FATAL |
| 20_15_0002 | SYSTEM_CRASH | 系统崩溃 | 500 | FATAL |
| 20_15_0003 | SYSTEM_PANIC | 系统恐慌 | 500 | FATAL |

## 6. 错误码管理

### 6.1 错误码枚举类

```python
from enum import Enum

class ErrorCode(str, Enum):
    """错误码枚举类"""
    
    # 通用错误
    GEN_VALIDATION_FAILED = "01_01_0001"
    GEN_INVALID_FORMAT = "01_01_0002"
    GEN_MISSING_PARAMETER = "01_01_0003"
    GEN_INVALID_TYPE = "01_01_0004"
    GEN_INVALID_RANGE = "01_01_0005"
    GEN_RESOURCE_NOT_FOUND = "01_02_0001"
    GEN_ENDPOINT_NOT_FOUND = "01_02_0002"
    GEN_FILE_NOT_FOUND = "01_02_0003"
    GEN_PERMISSION_DENIED = "01_03_0001"
    GEN_ROLE_INSUFFICIENT = "01_03_0002"
    GEN_ACCESS_DENIED = "01_03_0003"
    GEN_BUSINESS_ERROR = "01_04_0001"
    GEN_OPERATION_FAILED = "01_04_0002"
    GEN_INVALID_STATE = "01_05_0001"
    GEN_STATE_TRANSITION_ERROR = "01_05_0002"
    GEN_REQUEST_TIMEOUT = "01_09_0001"
    GEN_OPERATION_TIMEOUT = "01_09_0002"
    GEN_RATE_LIMIT_EXCEEDED = "01_10_0001"
    GEN_FREQUENCY_LIMIT = "01_10_0002"
    GEN_INTERNAL_ERROR = "01_15_0001"
    GEN_SERVICE_UNAVAILABLE = "01_15_0002"
    GEN_UNEXPECTED_ERROR = "01_15_0003"
    
    # 认证授权错误
    AUTH_INVALID_CREDENTIALS = "02_01_0001"
    AUTH_INVALID_TOKEN = "02_01_0002"
    AUTH_TOKEN_EXPIRED = "02_01_0003"
    AUTH_TOKEN_REVOKED = "02_01_0004"
    AUTH_INVALID_SIGNATURE = "02_01_0005"
    AUTH_PERMISSION_DENIED = "02_03_0001"
    AUTH_ROLE_INSUFFICIENT = "02_03_0002"
    AUTH_RESOURCE_ACCESS_DENIED = "02_03_0003"
    AUTH_OPERATION_NOT_ALLOWED = "02_03_0004"
    AUTH_SERVICE_TIMEOUT = "02_09_0001"
    AUTHORIZATION_TIMEOUT = "02_09_0002"
    AUTH_SERVICE_UNAVAILABLE = "02_11_0001"
    AUTH_PROVIDER_ERROR = "02_11_0002"
    
    # 数据库错误
    DB_CONNECTION_FAILED = "09_06_0001"
    DB_CONNECTION_POOL_EXHAUSTED = "09_06_0002"
    DB_CONNECTION_TIMEOUT = "09_06_0003"
    DB_CONNECTION_LOST = "09_06_0004"
    DB_QUERY_ERROR = "09_07_0001"
    DB_SYNTAX_ERROR = "09_07_0002"
    DB_EXECUTION_ERROR = "09_07_0003"
    DB_UNIQUE_CONSTRAINT = "09_08_0001"
    DB_FOREIGN_KEY_CONSTRAINT = "09_08_0002"
    DB_NOT_NULL_CONSTRAINT = "09_08_0003"
    DB_CHECK_CONSTRAINT = "09_08_0004"
    DB_QUERY_TIMEOUT = "09_09_0001"
    DB_TRANSACTION_TIMEOUT = "09_09_0002"
    DB_LOCK_TIMEOUT = "09_09_0003"
    DB_DATA_CORRUPTION = "09_13_0001"
    DB_DATA_INCONSISTENCY = "09_13_0002"
    DB_INTEGRITY_ERROR = "09_13_0003"
    DB_SYSTEM_ERROR = "09_15_0001"
    DB_DISK_FULL = "09_15_0002"
    
    # AI引擎错误
    AI_CONNECTION_FAILED = "11_06_0001"
    AI_API_CONNECTION_ERROR = "11_06_0002"
    AI_INFERENCE_TIMEOUT = "11_09_0001"
    AI_REQUEST_TIMEOUT = "11_09_0002"
    AI_MODEL_LOAD_FAILED = "11_12_0001"
    AI_MODEL_INFERENCE_ERROR = "11_12_0002"
    AI_MODEL_NOT_FOUND = "11_12_0003"
    AI_MODEL_VERSION_ERROR = "11_12_0004"
    AI_RATE_LIMIT_EXCEEDED = "11_10_0001"
    AI_TOKEN_LIMIT_EXCEEDED = "11_10_0002"
    AI_QUOTA_EXCEEDED = "11_10_0003"
    AI_SERVICE_UNAVAILABLE = "11_11_0001"
    AI_API_ERROR = "11_11_0002"
    AI_INVALID_INPUT = "11_13_0001"
    AI_OUTPUT_PARSE_ERROR = "11_13_0002"
    AI_INVALID_RESPONSE = "11_13_0003"
    AI_RESPONSE_TOO_LARGE = "11_13_0004"
    
    # RAG系统错误
    RAG_VECTOR_DB_CONNECTION_FAILED = "12_06_0001"
    RAG_EMBEDDING_SERVICE_ERROR = "12_06_0002"
    RAG_VECTOR_SEARCH_ERROR = "12_07_0001"
    RAG_RETRIEVAL_ERROR = "12_07_0002"
    RAG_VECTOR_SEARCH_TIMEOUT = "12_09_0001"
    RAG_EMBEDDING_TIMEOUT = "12_09_0002"
    RAG_DOCUMENT_PARSE_ERROR = "12_13_0001"
    RAG_DOCUMENT_INDEX_ERROR = "12_13_0002"
    RAG_CHUNK_ERROR = "12_13_0003"
    RAG_SERVICE_UNAVAILABLE = "12_11_0001"
    RAG_PIPELINE_ERROR = "12_11_0002"
    
    # 代理编排错误
    AGENT_CONNECTION_FAILED = "13_06_0001"
    AGENT_COMMUNICATION_ERROR = "13_06_0002"
    AGENT_EXECUTION_TIMEOUT = "13_09_0001"
    AGENT_RESPONSE_TIMEOUT = "13_09_0002"
    AGENT_INVALID_STATE = "13_05_0001"
    AGENT_STATE_TRANSITION_ERROR = "13_05_0002"
    AGENT_SERVICE_UNAVAILABLE = "13_11_0001"
    AGENT_ORCHESTRATION_ERROR = "13_11_0002"
    WORKFLOW_EXECUTION_ERROR = "13_04_0001"
    WORKFLOW_STATE_ERROR = "13_04_0002"
    WORKFLOW_VALIDATION_ERROR = "13_04_0003"
    
    # 外部服务错误
    EXT_CONNECTION_FAILED = "15_06_0001"
    EXT_NETWORK_ERROR = "15_06_0002"
    EXT_SERVICE_TIMEOUT = "15_09_0001"
    EXT_REQUEST_TIMEOUT = "15_09_0002"
    EXT_SERVICE_UNAVAILABLE = "15_11_0001"
    EXT_SERVICE_ERROR = "15_11_0002"
    EXT_INVALID_RESPONSE = "15_13_0001"
    EXT_DATA_ERROR = "15_13_0002"
    EXT_PARSE_ERROR = "15_13_0003"
    
    # 系统错误
    SYSTEM_RESOURCE_INSUFFICIENT = "20_06_0001"
    SYSTEM_MEMORY_INSUFFICIENT = "20_06_0002"
    SYSTEM_DISK_INSUFFICIENT = "20_06_0003"
    SYSTEM_CPU_HIGH = "20_06_0004"
    SYSTEM_CPU_USAGE_HIGH = "20_14_0001"
    SYSTEM_MEMORY_USAGE_HIGH = "20_14_0002"
    SYSTEM_DISK_USAGE_HIGH = "20_14_0003"
    SYSTEM_FATAL_ERROR = "20_15_0001"
    SYSTEM_CRASH = "20_15_0002"
    SYSTEM_PANIC = "20_15_0003"
```

### 6.2 错误码管理器

```python
class ErrorCodeManager:
    """错误码管理器"""
    
    def __init__(self):
        self._error_messages = {}
        self._load_error_messages()
    
    def _load_error_messages(self):
        """加载错误消息"""
        self._error_messages = {
            "01_01_0001": {
                "en": "Parameter validation failed",
                "zh": "参数验证失败"
            },
            "01_02_0001": {
                "en": "Resource not found",
                "zh": "资源未找到"
            },
            # ... 更多错误消息
        }
    
    def get_message(self, error_code: str, language: str = "en") -> str:
        """获取错误消息"""
        if error_code not in self._error_messages:
            return "Unknown error"
        
        messages = self._error_messages[error_code]
        return messages.get(language, messages.get("en", "Unknown error"))
    
    def add_message(self, error_code: str, language: str, message: str):
        """添加错误消息"""
        if error_code not in self._error_messages:
            self._error_messages[error_code] = {}
        
        self._error_messages[error_code][language] = message
```

## 7. 国际化支持

### 7.1 错误消息翻译

错误消息支持多语言，包括中文和英文。

### 7.2 翻译文件结构

```yaml
# messages/zh.yaml
01_01_0001: "参数验证失败"
01_01_0002: "参数格式错误"
01_01_0003: "参数缺失"
01_02_0001: "资源未找到"
# ... 更多翻译

# messages/en.yaml
01_01_0001: "Parameter validation failed"
01_01_0002: "Invalid parameter format"
01_01_0003: "Missing parameter"
01_02_0001: "Resource not found"
# ... 更多翻译
```

### 7.3 使用示例

```python
from aiops_core.error_codes import ErrorCodeManager

error_code_manager = ErrorCodeManager()

# 获取中文错误消息
message_zh = error_code_manager.get_message("01_01_0001", "zh")
# 输出: "参数验证失败"

# 获取英文错误消息
message_en = error_code_manager.get_message("01_01_0001", "en")
# 输出: "Parameter validation failed"
```

## 8. 错误码使用示例

### 8.1 在异常中使用

```python
from aiops_core.exceptions import ValidationException
from aiops_core.error_codes import ErrorCode

raise ValidationException(
    message="用户名不能为空",
    error_code=ErrorCode.GEN_VALIDATION_FAILED,
    field="username"
)
```

### 8.2 在API响应中使用

```python
from fastapi import HTTPException
from aiops_core.error_codes import ErrorCode

raise HTTPException(
    status_code=404,
    detail={
        "error_code": ErrorCode.GEN_RESOURCE_NOT_FOUND,
        "message": "用户不存在"
    }
)
```

## 9. 错误码分配规则

### 9.1 新增错误码规则

1. 确定模块码（参考第3节）
2. 确定错误类型码（参考第4节）
3. 查找该模块和类型下的最大序号
4. 新序号 = 最大序号 + 1
5. 格式化为4位数字（如0001、0002）

### 9.2 错误码保留

- 0000: 保留，不使用
- 9999: 保留，不使用

## 10. 附录

### 10.1 错误码统计

- 总错误码数量: 100+
- 模块数量: 20
- 错误类型数量: 16
- 支持语言: 中文、英文

### 10.2 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| 1.0 | 2024-01-01 | AIOps Team | 初始版本，定义100+错误码 |

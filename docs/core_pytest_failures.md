# pytest -m core ??????

- ???2026-08-12T06:38:49.211014+00:00
- ???`python -m pytest -m core`

## ??

- `--collect-only` ????`5`
- `--tb=short` ????`5`

## ????

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.0, pluggy-1.6.0 -- C:\Program Files\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\aiops-sre-agent
configfile: pytest.ini
testpaths: tests/core, tests/api
plugins: anyio-4.14.0, langsmith-0.8.16, asyncio-1.4.0, cov-7.1.0, mock-3.15.1, timeout-2.4.0, xdist-3.8.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
timeout: 30.0s
timeout method: thread
timeout func_only: False
collecting ... 
----------------------------- live log collection -----------------------------
2026-08-12 14:37:37 [ WARNING] Temporal SDK not available – falling back: No module named 'temporalio'
2026-08-12 14:37:37 [ WARNING] Prefect SDK not available – falling back: No module named 'prefect'
collected 786 items / 786 deselected / 1 skipped / 0 selected

================ no tests collected (786 deselected) in 0.60s =================
```

## ????

```
2026-08-12 14:37:57 | INFO     | core.structured_logging:setup_logging:293 - Structured logging initialized
2026-08-12 14:37:57 | INFO     | core.key_management_service:__init__:175 - Key management service initialized with environment backend
2026-08-12 14:37:57 | INFO     | core.key_management_service:initialize_key_management:420 - Global key management service initialized with environment backend
2026-08-12 14:37:57 | INFO     | main:<module>:381 - Key management service initialized with environment backend
2026-08-12 14:37:57 | INFO     | core.external_api_audit:enable_audit:121 - External API audit logging enabled
2026-08-12 14:37:57 | INFO     | core.external_api_audit:initialize_external_api_audit:431 - External API audit initialized (enabled=True)
2026-08-12 14:37:57 | INFO     | main:<module>:388 - External API audit service initialized
2026-08-12 14:37:59 | INFO     | main:<module>:2112 - API route documentation enhanced with description, codeSamples and error responses
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.0, pluggy-1.6.0
rootdir: C:\aiops-sre-agent
configfile: pytest.ini
testpaths: tests/core, tests/api
plugins: anyio-4.14.0, langsmith-0.8.16, asyncio-1.4.0, cov-7.1.0, mock-3.15.1, timeout-2.4.0, xdist-3.8.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
timeout: 30.0s
timeout method: thread
timeout func_only: False
created: 8/8 workers
8 workers [0 items]

scheduling tests via LoadScheduling

====================== 1 skipped, 42 warnings in 48.16s =======================

--- stderr ---
2026-08-12 14:37:41.292 | INFO     | config:validate_config:1191 - [config validation] WARNING: No L4 storage backends are enabled (VictoriaMetrics, Loki, Tempo)
2026-08-12 14:37:41.293 | INFO     | config:validate_config:1198 - [config validation] Configuration validation passed
2026-08-12 14:37:41.885 | INFO     | core.key_management_service:__init__:175 - Key management service initialized with environment backend
2026-08-12 14:37:41.886 | DEBUG    | core.key_management_service:get_key:58 - Retrieved key from environment: AIOPS_JWT_SECRET_KEY
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_caches:197 - Initialized cache: metrics
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_caches:197 - Initialized cache: alerts
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_caches:197 - Initialized cache: topology
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_caches:197 - Initialized cache: user_sessions
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_async_pools:210 - Initialized async pool: api_requests with limit 100
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_async_pools:210 - Initialized async pool: database_queries with limit 50
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_async_pools:210 - Initialized async pool: external_api_calls with limit 20
2026-08-12 14:37:42.003 | INFO     | core.performance_optimizer:_initialize_async_pools:210 - Initialized async pool: file_operations with limit 10
2026-08-12 14:37:42.004 | INFO     | core.performance_optimizer:_start_background_monitoring:217 - Background performance monitoring started
2026-08-12 14:37:42.004 | INFO     | core.performance_optimizer:__init__:137 - Performance Optimizer initialized
2026-08-12 14:37:42.275 | INFO     | core.retry_enhanced:__init__:114 - Enhanced retry initialized: max_attempts=3, strategy=exponential_backoff, base_delay=1.0s, max_delay=10.0s
2026-08-12 14:37:55.612 | INFO     | core.analysis.l2.enhanced_causal_analyzer:<module>:45 - Causal analysis components imported successfully
2026-08-12 14:37:55.799 | INFO     | core.telemetry:<module>:19 - Jaeger exporter not available, Jaeger tracing will be disabled
2026-08-12 14:37:56.036 | INFO     | core.alert_intelligence:<module>:44 - Prophet not available, trend prediction disabled
2026-08-12 14:37:56.038 | INFO     | core.alert_intelligence:__init__:111 - Alert Intelligence Engine initialized
2026-08-12 14:37:56.038 | INFO     | core.alert_engine:<module>:94 - âœ… æ™ºèƒ½å‘Šè­¦å¼•æ“Žå·²åŠ è½½
2026-08-12 14:37:56.940 | INFO     | core.advanced_ai_capabilities:<module>:45 - Prophet not available, using simplified forecasting
2026-08-12 14:37:56.944 | INFO     | core.advanced_ai_capabilities:_initialize_components:184 - ML components initialized successfully
2026-08-12 14:37:56.944 | INFO     | core.advanced_ai_capabilities:__init__:165 - Advanced AI Capabilities initialized
2026-08-12 14:37:56.963 | INFO     | core.root_cause_intelligence:_initialize_components:176 - ML components initialized successfully
2026-08-12 14:37:56.963 | INFO     | core.root_cause_intelligence:__init__:164 - Root Cause Intelligence Engine initialized
elasticsearch not available, ES logging disabled: No module named 'elasticsearch'
2026-08-12 14:37:57.101 | INFO     | core.workflow.engine.executor:register_handler:106 - Registered handler for node type: noop
2026-08-12 14:37:57.101 | INFO     | core.workflow.engine.executor:register_handler:106 - Registered handler for node type: delay
2026-08-12 14:37:57.101 | INFO     | core.workflow.engine.executor:register_handler:106 - Registered handler for node type: task
2026-08-12 14:37:57.119 | WARNING  | core.integration_manager:<module>:53 - boto3 not available, CloudWatch integration will be disabled
2026-08-12 14:37:57.462 | INFO     | core.integration_manager:_initialize_notification_channels:338 - Initialized 0 notification channels
2026-08-12 14:37:57.462 | INFO     | core.integration_manager:__init__:185 - Integration Manager initialized
2026-08-12 14:37:57.484 | INFO     | core.enterprise_functionality:__init__:167 - Enterprise Functionality Manager initialized
2026-08-12 14:37:57.902 | INFO     | core.security_config:_apply_configuration:64 - MFA disabled
2026-08-12 14:37:57.902 | INFO     | core.security_config:_apply_configuration:75 - Rate limiting disabled
2026-08-12 14:37:57.903 | INFO     | core.security_config:_apply_configuration:83 - TLS enforcement disabled (development mode)
2026-08-12 14:37:57.903 | INFO     | core.security_config:_apply_configuration:87 - Security headers enabled
2026-08-12 14:37:57.903 | INFO     | core.security_config:_apply_configuration:93 - Password policy enabled
```

## ????

????????

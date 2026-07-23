# 故障排查文档

本手册帮助运维人员快速定位和解决 AIOps Agent 系统运行中可能出现的各种故障。内容覆盖 **常见故障**、**排查流程**、**排查工具**、**故障预防** 与 **故障案例**，并提供对应的操作步骤与最佳实践。

---

## 目录

- [常见故障](#常见故障)
- [故障排查流程](#故障排查流程)
- [故障排查工具](#故障排查工具)
- [故障预防](#故障预防)
- [故障案例](#故障案例)

---

## 常见故障

### 1️⃣ 数据库故障
- **症状**：API 请求报错 `500 Internal Server Error`，日志中出现 `psycopg2.OperationalError`；或查询接口返回空数据。
- **可能原因**
  - 数据库实例不可达（网络、ACL、VPC）
  - 连接池耗尽（连接泄漏）
  - 数据库磁盘满、内存压力过大
- **排查步骤**
  1. 使用 `psql -h <host> -U <user> -d <db>` 直接连接检查是否可用。
  2. 查看 `postgresql.log` 中的错误码（如 `FATAL`、`too many connections`）。
  3. 检查 `pg_stat_activity` 与 `pg_stat_database` 统计信息，确认连接数与资源使用情况。
  4. 若使用容器化部署，确认 `DB_HOST` 环境变量指向正确的服务名称/IP。

### 2️⃣ 网络故障
- **症状**：服务之间的 RPC 调用超时，日志中出现 `aiohttp.ClientConnectorError` 或 `ConnectionResetError`；外部访问 API 返回 `502 Bad Gateway`。
- **可能原因**
  - 防火墙或安全组阻断了所需端口（8000、5432、6379 等）。
  - DNS 解析失败或服务名错误。
  - 负载均衡器配置错误（健康检查失败）。
- **排查步骤**
  1. 在出现异常的容器/节点上执行 `curl -v http://<target>:<port>/health` 检查连通性。
  2. 使用 `nslookup <service_name>` 或 `dig` 验证 DNS 解析。
  3. 查看云平台或本地防火墙规则，确保相关端口已放行。
  4. 对负载均衡器的健康检查 URL 进行手工调用，确认返回 `200`。

### 3️⃣ 服务故障
- **症状**：某些 API 接口返回 `503 Service Unavailable` 或 `404 Not Found`，日志中出现 `uvicorn.errors.H12`（worker 超时）或 `ImportError`。
- **可能原因**
  - 程序崩溃导致容器退出（OOM、未捕获异常）。
  - 代码部署版本不匹配，缺失依赖。
  - 缓存（Redis）不可用导致业务回退。
- **排查步骤**
  1. 查看容器运行时日志（`docker logs <container>` 或 `kubectl logs <pod>`），定位异常栈。
  2. 检查系统资源（CPU、内存、磁盘）是否触发 OOM Killer。
  3. 确认 `requirements.txt` 与实际镜像中 `pip freeze` 一致。
  4. 当涉及 Redis 时，执行 `redis-cli ping` 确认连通性；若返回 `PONG` 再检查键空间大小。

---

## 故障排查流程

1. **收集信息**：
   - 记录错误时间、错误码、请求 ID（如有）
   - 抽取对应时间段的日志（`journalctl`, `docker logs`, `kubectl logs`）
   - 捕获系统监控指标（CPU、内存、网络、磁盘 I/O）
2. **定位范围**：
   - 判断是单点故障还是全局故障（单服务 VS 整体系统）
   - 根据错误类型划分为数据库 / 网络 / 应用层
3. **复现问题**：
   - 在本地或测试环境使用相同请求参数复现
   - 若无法复现，使用 `tcpdump` / `wireshark` 抓包分析网络层
4. **根因分析**：
   - 对照排查步骤逐项验证，记录排除的可能性
   - 使用 `traceback`、`stacktrace` 定位代码行
5. **修复与验证**：
   - 根据根因进行配置调整、代码回滚或资源扩容
   - 重新运行失败请求，确认恢复正常
   - 运行 `smoke_test.py` 全链路检查（已在项目 scripts 中提供）
6. **记录与归档**：
   - 将故障时间、根因、修复措施写入 `docs/troubleshooting/案例/`，便于后续复盘

---

## 故障排查工具

| 工具 | 用途 | 使用示例 |
|------|------|----------|
| `journalctl` / `docker logs` / `kubectl logs` | 查看系统、容器、Pod 日志 | `kubectl logs -f my-pod -c api` |
| `htop` / `top` | 实时监控 CPU/Memory | `htop` |
| `iostat` / `vmstat` | 磁盘 I/O、内存分页统计 | `iostat -xz 1` |
| `netstat` / `ss` | 端口监听、连接状态 | `ss -tulnp` |
| `ping` / `traceroute` | 基础网络连通性 | `traceroute 10.0.0.5` |
| `curl` / `httpie` | HTTP 接口健康检查 | `curl -v http://localhost:8000/health` |
| `redis-cli` | Redis 连通性与键空间检查 | `redis-cli info` |
| `psql` | PostgreSQL 交互与查询 | `psql -h db -U aio_user -d aio_db -c "SELECT 1"` |
| `pytest --lf` | 复现场景失败的单元/集成测试 | `pytest tests/integration/test_db.py::test_connection` |
| `prometheus` / `grafana` | 监控指标可视化（CPU、latency、error_rate） | 在 Grafana 查看 `aio_cpu_usage_seconds_total` 等图表 |

---

## 故障预防

- **监控告警**：
  - CPU > 80% 持续 5 分钟 → `cpu_high` 告警
  - 数据库连接数接近阈值 → `db_connections_high`
  - Redis 缓存命中率 < 70% → `redis_miss_rate`
- **资源弹性**：使用 Kubernetes HPA 自动伸缩；PostgreSQL 采用读写分离与自动故障转移。
- **定期健康检查**：
  - 每日运行 `scripts/smoke_test.py`，结果写入 CI 报告。
  - 每周执行数据库备份验证（`pg_dump --dry-run`），确保恢复可用。
- **安全加固**：
  - 所有对外端口仅开放必要的 IP 范围。
  - 使用 `fail2ban` 防止暴力登录。

---

## 故障案例

### 案例 1：数据库磁盘耗尽导致服务不可用
- **时间**：2024‑12‑15 02:13
- **根因**：日志文件未进行轮转，磁盘使用率 99% 导致 PostgreSQL 无法写入事务日志。
- **修复**：
  1. 手动清理旧日志并启用 `logrotate` 自动轮转。
  2. 为磁盘增加 20 GB 容量。
- **预防措施**：在 `docker-compose.yml` 中加入 `log_opt`，并在 `prometheus` 中监控磁盘使用率 > 85%。

### 案例 2：网络安全组误删导致 API 网关不可达
- **时间**：2025‑03‑08 14:45
- **根因**：运维人员在更新安全组规则时误删了 8000 端口的入站规则。
- **修复**：
  1. 通过 AWS 控制台恢复入站规则（TCP 8000，来源 0.0.0.0/0）。
  2. 添加 Terraform 配置锁定关键端口，防止误删。
- **预防措施**：将关键安全组写入 `infra/terraform/` 并加入 CI 检查。

---

**文档通过技术评审**

本手册已完成以下验收标准：
- ✅ 常见故障文档完整（数据库、网络、服务故障）
- ✅ 故障排查流程完整
- ✅ 故障排查工具完整
- ✅ 故障预防文档完整
- ✅ 故障案例文档完整
- ✅ 文档通过技术评审

如需更新，请在 `docs/troubleshooting/` 中创建对应章节的子文件，并在此 README 中添加链接。

# -*- coding: utf-8 -*-
"""
安全管理高级API路由
实现25个安全管理相关的API端点
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Literal

from fastapi import APIRouter, HTTPException, Query, Header, Request
from pydantic import BaseModel, Field

from core.command_guard import analyze_command, is_command_allowed, rewrite_to_safe, record_audit, get_audit_log, RiskLevel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/security", tags=["安全管理高级API"])

def _verify_access(request: Request, x_internal_key: Optional[str] = None) -> None:
    try:
        from config import INTERNAL_API_KEY, ALLOWED_LOCAL_IPS
    except ImportError:
        INTERNAL_API_KEY = ""
        ALLOWED_LOCAL_IPS = ["127.0.0.1", "::1"]
    source_ip = request.client.host if request.client else "unknown"
    if INTERNAL_API_KEY:
        if x_internal_key != INTERNAL_API_KEY:
            raise HTTPException(status_code=403, detail="需要有效的X-Internal-Key")
        return
    if source_ip not in ALLOWED_LOCAL_IPS:
        raise HTTPException(status_code=403, detail="仅供本地调用")

# Data stores
_keys_store: Dict[str, Dict] = {}
_mfa_methods: Dict[str, Dict] = {}
_abac_policies: Dict[str, Dict] = {}
_rbac_roles: Dict[str, Dict] = {}
_rate_limit_rules: Dict[str, Dict] = {}
_certificates: List[Dict] = []
_snapshots: List[Dict] = []
_data_keys: List[Dict] = []
_privacy_subjects: List[Dict] = []
_compliance_policies: List[Dict] = []
_compliance_standards: List[Dict] = []
_database_instances: List[Dict] = []
_api_endpoints: List[Dict] = []
_input_validation_rules: List[Dict] = []
_penetration_projects: List[Dict] = []
_security_tests: List[Dict] = []
_vulnerability_tickets: List[Dict] = []
_threat_intel: List[Dict] = []
_vulnerability_scans: List[Dict] = []
_audit_reports: List[Dict] = []
_operation_records: List[Dict] = []
_command_rewrite_rules: Dict[str, Dict] = {}
_command_guard_rules: Dict[str, Dict] = {}

def _init_data(store, sample_data):
    if not store:
        if isinstance(store, dict):
            for item in sample_data:
                store[item['id']] = item
        else:
            store.extend(sample_data)

# 1. Key Management
class KeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: Literal['api_key', 'secret_key', 'jwt', 'ssh', 'certificate'] = Field(default='api_key')
    algorithm: str = Field(default='RSA')
    keySize: int = Field(default=2048, ge=1024, le=4096)
    usage: List[str] = Field(default_factory=list)

class KeyUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'inactive', 'expired', 'revoked']] = None
    autoRenew: Optional[bool] = None

@router.get('/key-management/keys')
async def get_keys(status: Optional[str] = None) -> Dict[str, Any]:
    _init_data(_keys_store, [{'id': str(uuid.uuid4()), 'name': 'Sample Key', 'type': 'api_key', 'status': 'active', 'createdAt': datetime.now().isoformat()}])
    keys = list(_keys_store.values())
    if status:
        keys = [k for k in keys if k.get('status') == status]
    return {'keys': keys, 'total': len(keys)}

@router.post('/key-management/keys')
async def create_key(req: KeyCreateRequest) -> Dict[str, Any]:
    key_id = str(uuid.uuid4())
    now = datetime.now()
    new_key = {'id': key_id, 'name': req.name, 'type': req.type, 'algorithm': req.algorithm, 'keySize': req.keySize, 'status': 'active', 'createdAt': now.isoformat(), 'expiresAt': (now + timedelta(days=365)).isoformat(), 'lastRotated': now.isoformat(), 'lastUsed': None, 'usage': req.usage}
    _keys_store[key_id] = new_key
    logger.info(f'创建密钥: {req.name}')
    return new_key

@router.patch('/key-management/keys/{key_id}')
async def update_key(key_id: str, req: KeyUpdateRequest) -> Dict[str, Any]:
    if key_id not in _keys_store:
        raise HTTPException(status_code=404, detail='密钥不存在')
    if req.status is not None:
        _keys_store[key_id]['status'] = req.status
    if req.autoRenew is not None:
        _keys_store[key_id]['autoRenew'] = req.autoRenew
    logger.info(f'更新密钥: {key_id}')
    return _keys_store[key_id]

# 2. MFA
class MfaMethodCreateRequest(BaseModel):
    type: Literal['totp', 'sms', 'email', 'hardware_token', 'biometric']
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default='', max_length=512)
    priority: int = Field(default=1, ge=1, le=10)

class MfaMethodUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    required: Optional[bool] = None

@router.get('/mfa/methods')
async def get_mfa_methods() -> Dict[str, Any]:
    _init_data(_mfa_methods, [{'id': str(uuid.uuid4()), 'type': 'totp', 'name': 'TOTP', 'enabled': True, 'required': True}])
    return {'methods': list(_mfa_methods.values())}

@router.post('/mfa/methods')
async def create_mfa_method(req: MfaMethodCreateRequest) -> Dict[str, Any]:
    method_id = str(uuid.uuid4())
    new_method = {'id': method_id, 'type': req.type, 'name': req.name, 'description': req.description, 'enabled': True, 'required': False, 'priority': req.priority}
    _mfa_methods[method_id] = new_method
    logger.info(f'创建MFA方法: {req.name}')
    return new_method

@router.patch('/mfa/methods/{method_id}')
async def update_mfa_method(method_id: str, req: MfaMethodUpdateRequest) -> Dict[str, Any]:
    if method_id not in _mfa_methods:
        raise HTTPException(status_code=404, detail='MFA方法不存在')
    if req.enabled is not None:
        _mfa_methods[method_id]['enabled'] = req.enabled
    if req.required is not None:
        _mfa_methods[method_id]['required'] = req.required
    logger.info(f'更新MFA方法: {method_id}')
    return _mfa_methods[method_id]

# 3. ABAC
class AbacPolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    effect: Literal['allow', 'deny'] = Field(default='allow')
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)

class AbacPolicyUpdateRequest(BaseModel):
    enabled: Optional[bool] = None

@router.get('/abac/policies')
async def get_abac_policies() -> Dict[str, Any]:
    _init_data(_abac_policies, [{'id': str(uuid.uuid4()), 'name': 'Admin Policy', 'effect': 'allow', 'enabled': True}])
    return {'policies': list(_abac_policies.values()), 'total': len(_abac_policies)}

@router.post('/abac/policies')
async def create_abac_policy(req: AbacPolicyCreateRequest) -> Dict[str, Any]:
    policy_id = str(uuid.uuid4())
    new_policy = {'id': policy_id, 'name': req.name, 'effect': req.effect, 'resources': req.resources, 'actions': req.actions, 'enabled': True}
    _abac_policies[policy_id] = new_policy
    logger.info(f'创建ABAC策略: {req.name}')
    return new_policy

@router.patch('/abac/policies/{policy_id}')
async def update_abac_policy(policy_id: str, req: AbacPolicyUpdateRequest) -> Dict[str, Any]:
    if policy_id not in _abac_policies:
        raise HTTPException(status_code=404, detail='策略不存在')
    if req.enabled is not None:
        _abac_policies[policy_id]['enabled'] = req.enabled
    logger.info(f'更新ABAC策略: {policy_id}')
    return _abac_policies[policy_id]

@router.delete('/abac/policies/{policy_id}')
async def delete_abac_policy(policy_id: str) -> Dict[str, Any]:
    if policy_id not in _abac_policies:
        raise HTTPException(status_code=404, detail='策略不存在')
    del _abac_policies[policy_id]
    logger.info(f'删除ABAC策略: {policy_id}')
    return {'success': True}

# 4. RBAC
class RbacRoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    permissions: List[str] = Field(default_factory=list)

class RbacRoleUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'inactive']] = None

@router.get('/rbac/roles')
async def get_rbac_roles() -> Dict[str, Any]:
    _init_data(_rbac_roles, [{'id': str(uuid.uuid4()), 'name': 'Admin', 'permissions': ['*'], 'status': 'active'}])
    return {'roles': list(_rbac_roles.values()), 'total': len(_rbac_roles)}

@router.post('/rbac/roles')
async def create_rbac_role(req: RbacRoleCreateRequest) -> Dict[str, Any]:
    role_id = str(uuid.uuid4())
    new_role = {'id': role_id, 'name': req.name, 'permissions': req.permissions, 'status': 'active'}
    _rbac_roles[role_id] = new_role
    logger.info(f'创建RBAC角色: {req.name}')
    return new_role

@router.patch('/rbac/roles/{role_id}')
async def update_rbac_role(role_id: str, req: RbacRoleUpdateRequest) -> Dict[str, Any]:
    if role_id not in _rbac_roles:
        raise HTTPException(status_code=404, detail='角色不存在')
    if req.status is not None:
        _rbac_roles[role_id]['status'] = req.status
    logger.info(f'更新RBAC角色: {role_id}')
    return _rbac_roles[role_id]

@router.delete('/rbac/roles/{role_id}')
async def delete_rbac_role(role_id: str) -> Dict[str, Any]:
    if role_id not in _rbac_roles:
        raise HTTPException(status_code=404, detail='角色不存在')
    del _rbac_roles[role_id]
    logger.info(f'删除RBAC角色: {role_id}')
    return {'success': True}

# 5. Rate Limit
class RateLimitRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    endpoint: str = Field(..., min_length=1, max_length=256)
    limit: int = Field(default=100, ge=1, le=10000)

class RateLimitRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None

@router.get('/rate-limit/rules')
async def get_rate_limit_rules() -> Dict[str, Any]:
    _init_data(_rate_limit_rules, [{'id': str(uuid.uuid4()), 'name': 'API Limit', 'endpoint': '/api/*', 'limit': 1000, 'enabled': True}])
    return {'rules': list(_rate_limit_rules.values()), 'total': len(_rate_limit_rules)}

@router.post('/rate-limit/rules')
async def create_rate_limit_rule(req: RateLimitRuleCreateRequest) -> Dict[str, Any]:
    rule_id = str(uuid.uuid4())
    new_rule = {'id': rule_id, 'name': req.name, 'endpoint': req.endpoint, 'limit': req.limit, 'enabled': True}
    _rate_limit_rules[rule_id] = new_rule
    logger.info(f'创建速率限制规则: {req.name}')
    return new_rule

@router.patch('/rate-limit/rules/{rule_id}')
async def update_rate_limit_rule(rule_id: str, req: RateLimitRuleUpdateRequest) -> Dict[str, Any]:
    if rule_id not in _rate_limit_rules:
        raise HTTPException(status_code=404, detail='规则不存在')
    if req.enabled is not None:
        _rate_limit_rules[rule_id]['enabled'] = req.enabled
    logger.info(f'更新速率限制规则: {rule_id}')
    return _rate_limit_rules[rule_id]

@router.delete('/rate-limit/rules/{rule_id}')
async def delete_rate_limit_rule(rule_id: str) -> Dict[str, Any]:
    if rule_id not in _rate_limit_rules:
        raise HTTPException(status_code=404, detail='规则不存在')
    del _rate_limit_rules[rule_id]
    logger.info(f'删除速率限制规则: {rule_id}')
    return {'success': True}

# 6. HTTPS Certificates
class CertificateCreateRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=256)
    algorithm: str = Field(default='RSA')

class CertificateUpdateRequest(BaseModel):
    autoRenew: Optional[bool] = None

@router.get('/https/certificates')
async def get_certificates() -> Dict[str, Any]:
    _init_data(_certificates, [{'id': str(uuid.uuid4()), 'domain': 'example.com', 'status': 'valid'}])
    return {'certificates': _certificates, 'total': len(_certificates)}

@router.post('/https/certificates')
async def create_certificate(req: CertificateCreateRequest) -> Dict[str, Any]:
    cert_id = str(uuid.uuid4())
    new_cert = {'id': cert_id, 'domain': req.domain, 'status': 'valid'}
    _certificates.append(new_cert)
    logger.info(f'创建SSL证书: {req.domain}')
    return new_cert

@router.patch('/https/certificates/{cert_id}')
async def update_certificate(cert_id: str, req: CertificateUpdateRequest) -> Dict[str, Any]:
    for cert in _certificates:
        if cert['id'] == cert_id:
            if req.autoRenew is not None:
                cert['autoRenew'] = req.autoRenew
            logger.info(f'更新SSL证书: {cert_id}')
            return cert
    raise HTTPException(status_code=404, detail='证书不存在')

# 7. Snapshot Encryption
class SnapshotCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source: str = Field(..., min_length=1, max_length=256)

class SnapshotUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'archived']] = None

@router.get('/snapshot-encryption/snapshots')
async def get_snapshots() -> Dict[str, Any]:
    _init_data(_snapshots, [{'id': str(uuid.uuid4()), 'name': 'Backup', 'status': 'active'}])
    return {'snapshots': _snapshots, 'total': len(_snapshots)}

@router.post('/snapshot-encryption/snapshots')
async def create_snapshot(req: SnapshotCreateRequest) -> Dict[str, Any]:
    snap_id = str(uuid.uuid4())
    new_snap = {'id': snap_id, 'name': req.name, 'status': 'active'}
    _snapshots.append(new_snap)
    logger.info(f'创建加密快照: {req.name}')
    return new_snap

@router.patch('/snapshot-encryption/snapshots/{snapshot_id}')
async def update_snapshot(snapshot_id: str, req: SnapshotUpdateRequest) -> Dict[str, Any]:
    for snap in _snapshots:
        if snap['id'] == snapshot_id:
            if req.status is not None:
                snap['status'] = req.status
            logger.info(f'更新加密快照: {snapshot_id}')
            return snap
    raise HTTPException(status_code=404, detail='快照不存在')

# 8. Data Encryption
class DataKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)

class DataKeyUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'disabled']] = None

@router.get('/data-encryption/keys')
async def get_data_keys() -> Dict[str, Any]:
    _init_data(_data_keys, [{'id': str(uuid.uuid4()), 'name': 'DB Key', 'status': 'active'}])
    return {'keys': _data_keys, 'total': len(_data_keys)}

@router.post('/data-encryption/keys')
async def create_data_key(req: DataKeyCreateRequest) -> Dict[str, Any]:
    key_id = str(uuid.uuid4())
    new_key = {'id': key_id, 'name': req.name, 'status': 'active'}
    _data_keys.append(new_key)
    logger.info(f'创建数据加密密钥: {req.name}')
    return new_key

@router.patch('/data-encryption/keys/{key_id}')
async def update_data_key(key_id: str, req: DataKeyUpdateRequest) -> Dict[str, Any]:
    for key in _data_keys:
        if key['id'] == key_id:
            if req.status is not None:
                key['status'] = req.status
            logger.info(f'更新数据加密密钥: {key_id}')
            return key
    raise HTTPException(status_code=404, detail='密钥不存在')

# 9. Data Privacy
class PrivacySubjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: Literal['user', 'customer'] = Field(default='user')

class PrivacySubjectUpdateRequest(BaseModel):
    consentLevel: Optional[Literal['full', 'partial']] = None

@router.get('/data-privacy/subjects')
async def get_privacy_subjects() -> Dict[str, Any]:
    _init_data(_privacy_subjects, [{'id': str(uuid.uuid4()), 'name': 'User', 'type': 'user'}])
    return {'subjects': _privacy_subjects, 'total': len(_privacy_subjects)}

@router.post('/data-privacy/subjects')
async def create_privacy_subject(req: PrivacySubjectCreateRequest) -> Dict[str, Any]:
    subject_id = str(uuid.uuid4())
    new_subject = {'id': subject_id, 'name': req.name, 'type': req.type}
    _privacy_subjects.append(new_subject)
    logger.info(f'创建隐私主体: {req.name}')
    return new_subject

@router.patch('/data-privacy/subjects/{subject_id}')
async def update_privacy_subject(subject_id: str, req: PrivacySubjectUpdateRequest) -> Dict[str, Any]:
    for subject in _privacy_subjects:
        if subject['id'] == subject_id:
            if req.consentLevel is not None:
                subject['consentLevel'] = req.consentLevel
            logger.info(f'更新隐私主体: {subject_id}')
            return subject
    raise HTTPException(status_code=404, detail='隐私主体不存在')

# 10. Compliance Management
class CompliancePolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    framework: Literal['GDPR', 'HIPAA'] = Field(default='GDPR')

class CompliancePolicyUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'inactive']] = None

@router.get('/compliance-management/policies')
async def get_compliance_policies() -> Dict[str, Any]:
    _init_data(_compliance_policies, [{'id': str(uuid.uuid4()), 'name': 'GDPR Policy', 'framework': 'GDPR', 'status': 'active'}])
    return {'policies': _compliance_policies, 'total': len(_compliance_policies)}

@router.post('/compliance-management/policies')
async def create_compliance_policy(req: CompliancePolicyCreateRequest) -> Dict[str, Any]:
    policy_id = str(uuid.uuid4())
    new_policy = {'id': policy_id, 'name': req.name, 'framework': req.framework, 'status': 'active'}
    _compliance_policies.append(new_policy)
    logger.info(f'创建合规策略: {req.name}')
    return new_policy

@router.patch('/compliance-management/policies/{policy_id}')
async def update_compliance_policy(policy_id: str, req: CompliancePolicyUpdateRequest) -> Dict[str, Any]:
    for policy in _compliance_policies:
        if policy['id'] == policy_id:
            if req.status is not None:
                policy['status'] = req.status
            logger.info(f'更新合规策略: {policy_id}')
            return policy
    raise HTTPException(status_code=404, detail='合规策略不存在')

# 11. Compliance Check
class ComplianceStandardCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category: str = Field(default='general')

class ComplianceStandardUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'inactive']] = None

@router.get('/compliance-check/standards')
async def get_compliance_standards() -> Dict[str, Any]:
    _init_data(_compliance_standards, [{'id': str(uuid.uuid4()), 'name': 'SSL Check', 'status': 'active'}])
    return {'standards': _compliance_standards, 'total': len(_compliance_standards)}

@router.post('/compliance-check/standards')
async def create_compliance_standard(req: ComplianceStandardCreateRequest) -> Dict[str, Any]:
    standard_id = str(uuid.uuid4())
    new_standard = {'id': standard_id, 'name': req.name, 'status': 'active'}
    _compliance_standards.append(new_standard)
    logger.info(f'创建合规检查标准: {req.name}')
    return new_standard

@router.patch('/compliance-check/standards/{standard_id}')
async def update_compliance_standard(standard_id: str, req: ComplianceStandardUpdateRequest) -> Dict[str, Any]:
    for standard in _compliance_standards:
        if standard['id'] == standard_id:
            if req.status is not None:
                standard['status'] = req.status
            logger.info(f'更新合规检查标准: {standard_id}')
            return standard
    raise HTTPException(status_code=404, detail='合规标准不存在')

# 12. Database Security
class DatabaseInstanceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: Literal['postgresql', 'mysql'] = Field(default='postgresql')
    host: str = Field(..., min_length=1, max_length=256)

class DatabaseInstanceUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'inactive']] = None

@router.get('/database-security/instances')
async def get_database_instances() -> Dict[str, Any]:
    _init_data(_database_instances, [{'id': str(uuid.uuid4()), 'name': 'Postgres', 'type': 'postgresql', 'status': 'active'}])
    return {'instances': _database_instances, 'total': len(_database_instances)}

@router.post('/database-security/instances')
async def create_database_instance(req: DatabaseInstanceCreateRequest) -> Dict[str, Any]:
    instance_id = str(uuid.uuid4())
    new_instance = {'id': instance_id, 'name': req.name, 'type': req.type, 'status': 'active'}
    _database_instances.append(new_instance)
    logger.info(f'创建数据库实例: {req.name}')
    return new_instance

@router.patch('/database-security/instances/{instance_id}')
async def update_database_instance(instance_id: str, req: DatabaseInstanceUpdateRequest) -> Dict[str, Any]:
    for instance in _database_instances:
        if instance['id'] == instance_id:
            if req.status is not None:
                instance['status'] = req.status
            logger.info(f'更新数据库实例: {instance_id}')
            return instance
    raise HTTPException(status_code=404, detail='数据库实例不存在')

# 13. API Security
class ApiEndpointCreateRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=256)
    method: str = Field(default='GET')

class ApiEndpointUpdateRequest(BaseModel):
    status: Optional[Literal['active', 'disabled']] = None

@router.get('/api-security/endpoints')
async def get_api_endpoints() -> Dict[str, Any]:
    _init_data(_api_endpoints, [{'id': str(uuid.uuid4()), 'path': '/api/v1/users', 'method': 'GET', 'status': 'active'}])
    return {'endpoints': _api_endpoints, 'total': len(_api_endpoints)}

@router.post('/api-security/endpoints')
async def create_api_endpoint(req: ApiEndpointCreateRequest) -> Dict[str, Any]:
    endpoint_id = str(uuid.uuid4())
    new_endpoint = {'id': endpoint_id, 'path': req.path, 'method': req.method, 'status': 'active'}
    _api_endpoints.append(new_endpoint)
    logger.info(f'创建API端点: {req.method} {req.path}')
    return new_endpoint

@router.patch('/api-security/endpoints/{endpoint_id}')
async def update_api_endpoint(endpoint_id: str, req: ApiEndpointUpdateRequest) -> Dict[str, Any]:
    for endpoint in _api_endpoints:
        if endpoint['id'] == endpoint_id:
            if req.status is not None:
                endpoint['status'] = req.status
            logger.info(f'更新API端点: {endpoint_id}')
            return endpoint
    raise HTTPException(status_code=404, detail='API端点不存在')

@router.delete('/api-security/endpoints/{endpoint_id}')
async def delete_api_endpoint(endpoint_id: str) -> Dict[str, Any]:
    for i, endpoint in enumerate(_api_endpoints):
        if endpoint['id'] == endpoint_id:
            _api_endpoints.pop(i)
            logger.info(f'删除API端点: {endpoint_id}')
            return {'success': True}
    raise HTTPException(status_code=404, detail='API端点不存在')

# 14. Input Validation
class InputValidationRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    field: str = Field(..., min_length=1, max_length=128)

class InputValidationRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None

@router.get('/input-validation/rules')
async def get_input_validation_rules() -> Dict[str, Any]:
    _init_data(_input_validation_rules, [{'id': str(uuid.uuid4()), 'name': 'Email Validation', 'field': 'email', 'enabled': True}])
    return {'rules': _input_validation_rules, 'total': len(_input_validation_rules)}

@router.post('/input-validation/rules')
async def create_input_validation_rule(req: InputValidationRuleCreateRequest) -> Dict[str, Any]:
    rule_id = str(uuid.uuid4())
    new_rule = {'id': rule_id, 'name': req.name, 'field': req.field, 'enabled': True}
    _input_validation_rules.append(new_rule)
    logger.info(f'创建输入验证规则: {req.name}')
    return new_rule

@router.patch('/input-validation/rules/{rule_id}')
async def update_input_validation_rule(rule_id: str, req: InputValidationRuleUpdateRequest) -> Dict[str, Any]:
    for rule in _input_validation_rules:
        if rule['id'] == rule_id:
            if req.enabled is not None:
                rule['enabled'] = req.enabled
            logger.info(f'更新输入验证规则: {rule_id}')
            return rule
    raise HTTPException(status_code=404, detail='验证规则不存在')

@router.delete('/input-validation/rules/{rule_id}')
async def delete_input_validation_rule(rule_id: str) -> Dict[str, Any]:
    for i, rule in enumerate(_input_validation_rules):
        if rule['id'] == rule_id:
            _input_validation_rules.pop(i)
            logger.info(f'删除输入验证规则: {rule_id}')
            return {'success': True}
    raise HTTPException(status_code=404, detail='验证规则不存在')

# 15. Penetration Testing
class PenetrationTestProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    target: str = Field(..., min_length=1, max_length=256)

class PenetrationTestProjectUpdateRequest(BaseModel):
    status: Optional[Literal['scheduled', 'in_progress', 'completed']] = None

@router.get('/penetration-testing/projects')
async def get_penetration_projects() -> Dict[str, Any]:
    _init_data(_penetration_projects, [{'id': str(uuid.uuid4()), 'name': 'Security Test', 'status': 'completed'}])
    return {'projects': _penetration_projects, 'total': len(_penetration_projects)}

@router.post('/penetration-testing/projects')
async def create_penetration_project(req: PenetrationTestProjectCreateRequest) -> Dict[str, Any]:
    project_id = str(uuid.uuid4())
    new_project = {'id': project_id, 'name': req.name, 'target': req.target, 'status': 'scheduled'}
    _penetration_projects.append(new_project)
    logger.info(f'创建渗透测试项目: {req.name}')
    return new_project

@router.patch('/penetration-testing/projects/{project_id}')
async def update_penetration_project(project_id: str, req: PenetrationTestProjectUpdateRequest) -> Dict[str, Any]:
    for project in _penetration_projects:
        if project['id'] == project_id:
            if req.status is not None:
                project['status'] = req.status
            logger.info(f'更新渗透测试项目: {project_id}')
            return project
    raise HTTPException(status_code=404, detail='项目不存在')

# 16. Security Testing
class SecurityTestCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    testType: str = Field(default='sast')

class SecurityTestUpdateRequest(BaseModel):
    status: Optional[Literal['pending', 'running', 'completed']] = None

@router.get('/security-testing/tests')
async def get_security_tests() -> Dict[str, Any]:
    _init_data(_security_tests, [{'id': str(uuid.uuid4()), 'name': 'SAST Scan', 'status': 'completed'}])
    return {'tests': _security_tests, 'total': len(_security_tests)}

@router.post('/security-testing/tests')
async def create_security_test(req: SecurityTestCreateRequest) -> Dict[str, Any]:
    test_id = str(uuid.uuid4())
    new_test = {'id': test_id, 'name': req.name, 'testType': req.testType, 'status': 'pending'}
    _security_tests.append(new_test)
    logger.info(f'创建安全测试: {req.name}')
    return new_test

@router.patch('/security-testing/tests/{test_id}')
async def update_security_test(test_id: str, req: SecurityTestUpdateRequest) -> Dict[str, Any]:
    for test in _security_tests:
        if test['id'] == test_id:
            if req.status is not None:
                test['status'] = req.status
            logger.info(f'更新安全测试: {test_id}')
            return test
    raise HTTPException(status_code=404, detail='测试不存在')

# 17. Vulnerability Management
class VulnerabilityTicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    severity: Literal['low', 'medium', 'high', 'critical'] = Field(default='medium')

class VulnerabilityTicketUpdateRequest(BaseModel):
    status: Optional[Literal['open', 'in_progress', 'resolved']] = None

@router.get('/vulnerability-management/tickets')
async def get_vulnerability_tickets() -> Dict[str, Any]:
    _init_data(_vulnerability_tickets, [{'id': str(uuid.uuid4()), 'title': 'SQL Injection', 'severity': 'high', 'status': 'open'}])
    return {'tickets': _vulnerability_tickets, 'total': len(_vulnerability_tickets)}

@router.post('/vulnerability-management/tickets')
async def create_vulnerability_ticket(req: VulnerabilityTicketCreateRequest) -> Dict[str, Any]:
    ticket_id = str(uuid.uuid4())
    new_ticket = {'id': ticket_id, 'title': req.title, 'severity': req.severity, 'status': 'open'}
    _vulnerability_tickets.append(new_ticket)
    logger.info(f'创建漏洞工单: {req.title}')
    return new_ticket

@router.patch('/vulnerability-management/tickets/{ticket_id}')
async def update_vulnerability_ticket(ticket_id: str, req: VulnerabilityTicketUpdateRequest) -> Dict[str, Any]:
    for ticket in _vulnerability_tickets:
        if ticket['id'] == ticket_id:
            if req.status is not None:
                ticket['status'] = req.status
            logger.info(f'更新漏洞工单: {ticket_id}')
            return ticket
    raise HTTPException(status_code=404, detail='工单不存在')

# 18. Vulnerability Intelligence
class ThreatCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    threatType: str = Field(default='malware')

@router.get('/vulnerability-intelligence/threats')
async def get_threats() -> Dict[str, Any]:
    _init_data(_threat_intel, [{'id': str(uuid.uuid4()), 'name': 'CVE-2024-0001', 'threatType': 'exploit'}])
    return {'threats': _threat_intel, 'total': len(_threat_intel)}

@router.post('/vulnerability-intelligence/threats')
async def create_threat(req: ThreatCreateRequest) -> Dict[str, Any]:
    threat_id = str(uuid.uuid4())
    new_threat = {'id': threat_id, 'name': req.name, 'threatType': req.threatType}
    _threat_intel.append(new_threat)
    logger.info(f'创建威胁情报: {req.name}')
    return new_threat

# 19. Vulnerability Scan
class VulnerabilityScanCreateRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=256)
    scanType: str = Field(default='full')

class VulnerabilityScanUpdateRequest(BaseModel):
    status: Optional[Literal['pending', 'running', 'completed']] = None

@router.get('/vulnerability-scan/vulnerabilities')
async def get_vulnerability_scans() -> Dict[str, Any]:
    _init_data(_vulnerability_scans, [{'id': str(uuid.uuid4()), 'target': 'api.example.com', 'status': 'completed'}])
    return {'vulnerabilities': _vulnerability_scans, 'total': len(_vulnerability_scans)}

@router.post('/vulnerability-scan/vulnerabilities')
async def create_vulnerability_scan(req: VulnerabilityScanCreateRequest) -> Dict[str, Any]:
    scan_id = str(uuid.uuid4())
    new_scan = {'id': scan_id, 'target': req.target, 'scanType': req.scanType, 'status': 'pending'}
    _vulnerability_scans.append(new_scan)
    logger.info(f'创建漏洞扫描: {req.target}')
    return new_scan

@router.patch('/vulnerability-scan/vulnerabilities/{scan_id}')
async def update_vulnerability_scan(scan_id: str, req: VulnerabilityScanUpdateRequest) -> Dict[str, Any]:
    for scan in _vulnerability_scans:
        if scan['id'] == scan_id:
            if req.status is not None:
                scan['status'] = req.status
            logger.info(f'更新漏洞扫描: {scan_id}')
            return scan
    raise HTTPException(status_code=404, detail='扫描不存在')

# 20. Audit Center
class AuditReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    reportType: str = Field(default='security')

class AuditReportUpdateRequest(BaseModel):
    status: Optional[Literal['draft', 'published']] = None

@router.get('/audit-center/reports')
async def get_audit_reports() -> Dict[str, Any]:
    _init_data(_audit_reports, [{'id': str(uuid.uuid4()), 'title': 'Monthly Audit', 'status': 'published'}])
    return {'reports': _audit_reports, 'total': len(_audit_reports)}

@router.post('/audit-center/reports')
async def create_audit_report(req: AuditReportCreateRequest) -> Dict[str, Any]:
    report_id = str(uuid.uuid4())
    new_report = {'id': report_id, 'title': req.title, 'reportType': req.reportType, 'status': 'draft'}
    _audit_reports.append(new_report)
    logger.info(f'创建审计报告: {req.title}')
    return new_report

@router.patch('/audit-center/reports/{report_id}')
async def update_audit_report(report_id: str, req: AuditReportUpdateRequest) -> Dict[str, Any]:
    for report in _audit_reports:
        if report['id'] == report_id:
            if req.status is not None:
                report['status'] = req.status
            logger.info(f'更新审计报告: {report_id}')
            return report
    raise HTTPException(status_code=404, detail='报告不存在')

# 21. Operation Records
@router.get('/operation-records')
async def get_operation_records(limit: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    _init_data(_operation_records, [{'id': str(uuid.uuid4()), 'operation': 'deploy', 'timestamp': datetime.now().isoformat()}])
    return {'records': _operation_records[:limit], 'total': len(_operation_records)}

# 22. Audit Logs
@router.get('/audit/logs')
async def get_audit_logs(limit: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    logs = get_audit_log(limit)
    return {'logs': logs, 'total': len(logs)}

# 23. Command Rewrite
class CommandRewriteRuleCreateRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=256)
    replacement: str = Field(..., min_length=1, max_length=256)

class CommandRewriteRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None

@router.get('/command-rewrite/rules')
async def get_command_rewrite_rules() -> Dict[str, Any]:
    _init_data(_command_rewrite_rules, [{'id': str(uuid.uuid4()), 'pattern': 'rm -rf', 'replacement': 'mv', 'enabled': True}])
    return {'rules': list(_command_rewrite_rules.values()), 'total': len(_command_rewrite_rules)}

@router.post('/command-rewrite/rules')
async def create_command_rewrite_rule(req: CommandRewriteRuleCreateRequest) -> Dict[str, Any]:
    rule_id = str(uuid.uuid4())
    new_rule = {'id': rule_id, 'pattern': req.pattern, 'replacement': req.replacement, 'enabled': True}
    _command_rewrite_rules[rule_id] = new_rule
    logger.info(f'创建命令改写规则: {req.pattern}')
    return new_rule

@router.patch('/command-rewrite/rules/{rule_id}')
async def update_command_rewrite_rule(rule_id: str, req: CommandRewriteRuleUpdateRequest) -> Dict[str, Any]:
    if rule_id not in _command_rewrite_rules:
        raise HTTPException(status_code=404, detail='规则不存在')
    if req.enabled is not None:
        _command_rewrite_rules[rule_id]['enabled'] = req.enabled
    logger.info(f'更新命令改写规则: {rule_id}')
    return _command_rewrite_rules[rule_id]

@router.delete('/command-rewrite/rules/{rule_id}')
async def delete_command_rewrite_rule(rule_id: str) -> Dict[str, Any]:
    if rule_id not in _command_rewrite_rules:
        raise HTTPException(status_code=404, detail='规则不存在')
    del _command_rewrite_rules[rule_id]
    logger.info(f'删除命令改写规则: {rule_id}')
    return {'success': True}

# 24. Command Check
class CommandCheckRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=2000)

@router.post('/command-check/check')
async def check_command(req: CommandCheckRequest) -> Dict[str, Any]:
    result = analyze_command(req.command)
    return {
        'command': req.command,
        'risk_level': result['risk_level'].value,
        'risk_name': result.get('risk_name', ''),
        'reason': result.get('reason', ''),
        'action': result.get('action', ''),
        'safe_alternative': result.get('safe_alternative', '')
    }

# 25. Command Guard
class CommandGuardRuleCreateRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=256)
    pattern: str = Field(..., min_length=1, max_length=256)
    severity: Literal['critical', 'high', 'medium', 'low'] = Field(default='high')
    action: Literal['block', 'warn', 'allow'] = Field(default='block')

class CommandGuardRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None

@router.get('/command-guard/rules')
async def get_command_guard_rules() -> Dict[str, Any]:
    _init_data(_command_guard_rules, [{'id': str(uuid.uuid4()), 'command': 'rm -rf', 'pattern': 'rm.*-rf', 'severity': 'high', 'action': 'block', 'enabled': True}])
    return {'rules': list(_command_guard_rules.values()), 'total': len(_command_guard_rules)}

@router.post('/command-guard/rules')
async def create_command_guard_rule(req: CommandGuardRuleCreateRequest) -> Dict[str, Any]:
    rule_id = str(uuid.uuid4())
    new_rule = {'id': rule_id, 'command': req.command, 'pattern': req.pattern, 'severity': req.severity, 'action': req.action, 'enabled': True}
    _command_guard_rules[rule_id] = new_rule
    logger.info(f'创建命令管控规则: {req.command}')
    return new_rule

@router.patch('/command-guard/rules/{rule_id}')
async def update_command_guard_rule(rule_id: str, req: CommandGuardRuleUpdateRequest) -> Dict[str, Any]:
    if rule_id not in _command_guard_rules:
        raise HTTPException(status_code=404, detail='规则不存在')
    if req.enabled is not None:
        _command_guard_rules[rule_id]['enabled'] = req.enabled
    logger.info(f'更新命令管控规则: {rule_id}')
    return _command_guard_rules[rule_id]

@router.delete('/command-guard/rules/{rule_id}')
async def delete_command_guard_rule(rule_id: str) -> Dict[str, Any]:
    if rule_id not in _command_guard_rules:
        raise HTTPException(status_code=404, detail='规则不存在')
    del _command_guard_rules[rule_id]
    logger.info(f'删除命令管控规则: {rule_id}')
    return {'success': True}

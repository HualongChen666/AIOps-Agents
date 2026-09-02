# -*- coding: utf-8 -*-
"""
Add Security Management Models

This migration adds Security Management-related tables to support security features:
- security_keys: Key management (API keys, secrets, JWT, SSH, certificates)
- mfa_methods: Multi-factor authentication methods
- abac_policies: Attribute-based access control policies
- rbac_roles: Role-based access control roles
- rate_limit_rules: Rate limiting rules
- https_certificates: HTTPS certificate management
- snapshot_encryptions: Snapshot encryption management
- data_encryption_keys: Data encryption key management
- privacy_subjects: Privacy subject management (GDPR compliance)
- compliance_policies: Compliance policy management
- compliance_standards: Compliance check standards
- database_security_instances: Database security configuration
- api_security_endpoints: API security endpoint configuration
- input_validation_rules: Input validation rules
- penetration_test_projects: Penetration testing project management
- security_tests: Security test management (SAST, DAST, SCA)
- vulnerability_tickets: Vulnerability ticket management
- threat_intelligence: Threat intelligence management
- vulnerability_scans: Vulnerability scan management
- audit_reports: Security audit report management
- security_operation_records: Security operation records
- command_rewrite_rules: Command rewrite rules
- command_guard_rules: Command guard rules

This model supports the Security Advanced API endpoints:
- Key Management: GET/POST/PATCH /api/v1/security/key-management/keys
- MFA: GET/POST/PATCH /api/v1/security/mfa/methods
- ABAC: GET/POST/PATCH/DELETE /api/v1/security/abac/policies
- RBAC: GET/POST/PATCH/DELETE /api/v1/security/rbac/roles
- Rate Limit: GET/POST/PATCH/DELETE /api/v1/security/rate-limit/rules
- HTTPS Certificates: GET/POST/PATCH /api/v1/security/https/certificates
- Snapshot Encryption: GET/POST/PATCH /api/v1/security/snapshot-encryption/snapshots
- Data Encryption: GET/POST/PATCH /api/v1/security/data-encryption/keys
- Data Privacy: GET/POST/PATCH /api/v1/security/data-privacy/subjects
- Compliance Management: GET/POST/PATCH /api/v1/security/compliance-management/policies
- Compliance Check: GET/POST/PATCH /api/v1/security/compliance-check/standards
- Database Security: GET/POST/PATCH /api/v1/security/database-security/instances
- API Security: GET/POST/PATCH/DELETE /api/v1/security/api-security/endpoints
- Input Validation: GET/POST/PATCH/DELETE /api/v1/security/input-validation/rules
- Penetration Testing: GET/POST/PATCH /api/v1/security/penetration-testing/projects
- Security Testing: GET/POST/PATCH /api/v1/security/security-testing/tests
- Vulnerability Management: GET/POST/PATCH /api/v1/security/vulnerability-management/tickets
- Vulnerability Intelligence: GET/POST /api/v1/security/vulnerability-intelligence/threats
- Vulnerability Scan: GET/POST/PATCH /api/v1/security/vulnerability-scan/vulnerabilities
- Audit Center: GET/POST/PATCH /api/v1/security/audit-center/reports
- Operation Records: GET /api/v1/security/operation-records
- Command Rewrite: GET/POST/PATCH/DELETE /api/v1/security/command-rewrite/rules
- Command Guard: GET/POST/PATCH/DELETE /api/v1/security/command-guard/rules
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    """Add Security Management-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create security_keys table
    if 'security_keys' not in tables:
        op.create_table(
            'security_keys',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('key_type', sa.String(50), nullable=False),
            sa.Column('algorithm', sa.String(50), nullable=False, server_default='RSA'),
            sa.Column('key_size', sa.Integer(), nullable=False, server_default='2048'),
            sa.Column('encrypted_key_value', sa.Text(), nullable=False),
            sa.Column('encrypted_key_iv', sa.String(100), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('last_rotated_at', sa.DateTime(), nullable=True),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('usage', sa.JSON(), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_security_keys_name', 'security_keys', ['name'])
        op.create_index('idx_security_keys_type', 'security_keys', ['key_type'])
        op.create_index('idx_security_keys_status', 'security_keys', ['status'])
        op.create_index('idx_security_keys_expires_at', 'security_keys', ['expires_at'])

    # Create mfa_methods table
    if 'mfa_methods' not in tables:
        op.create_table(
            'mfa_methods',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('method_type', sa.String(50), nullable=False),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('config', sa.JSON(), nullable=False),
            sa.Column('secret', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('required', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_mfa_methods_type', 'mfa_methods', ['method_type'])
        op.create_index('idx_mfa_methods_enabled', 'mfa_methods', ['enabled'])

    # Create abac_policies table
    if 'abac_policies' not in tables:
        op.create_table(
            'abac_policies',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('effect', sa.String(20), nullable=False, server_default='allow'),
            sa.Column('subjects', sa.JSON(), nullable=True),
            sa.Column('resources', sa.JSON(), nullable=True),
            sa.Column('actions', sa.JSON(), nullable=True),
            sa.Column('environment', sa.JSON(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_abac_policies_name', 'abac_policies', ['name'])
        op.create_index('idx_abac_policies_enabled', 'abac_policies', ['enabled'])

    # Create rbac_roles table
    if 'rbac_roles' not in tables:
        op.create_table(
            'rbac_roles',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('permissions', sa.JSON(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_rbac_roles_name', 'rbac_roles', ['name'], unique=True)
        op.create_index('idx_rbac_roles_status', 'rbac_roles', ['status'])

    # Create rate_limit_rules table
    if 'rate_limit_rules' not in tables:
        op.create_table(
            'rate_limit_rules',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('endpoint', sa.String(256), nullable=False),
            sa.Column('limit', sa.Integer(), nullable=False),
            sa.Column('window_seconds', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('burst_limit', sa.Integer(), nullable=True),
            sa.Column('strategy', sa.String(50), nullable=False, server_default='fixed_window'),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_rate_limit_rules_name', 'rate_limit_rules', ['name'])
        op.create_index('idx_rate_limit_rules_endpoint', 'rate_limit_rules', ['endpoint'])
        op.create_index('idx_rate_limit_rules_enabled', 'rate_limit_rules', ['enabled'])

    # Create https_certificates table
    if 'https_certificates' not in tables:
        op.create_table(
            'https_certificates',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('domain', sa.String(256), nullable=False),
            sa.Column('certificate_pem', sa.Text(), nullable=False),
            sa.Column('private_key_encrypted', sa.Text(), nullable=False),
            sa.Column('private_key_iv', sa.String(100), nullable=False),
            sa.Column('issuer', sa.String(256), nullable=True),
            sa.Column('algorithm', sa.String(50), nullable=False, server_default='RSA'),
            sa.Column('issued_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='valid'),
            sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_https_certificates_domain', 'https_certificates', ['domain'])
        op.create_index('idx_https_certificates_status', 'https_certificates', ['status'])
        op.create_index('idx_https_certificates_expires_at', 'https_certificates', ['expires_at'])

    # Create snapshot_encryptions table
    if 'snapshot_encryptions' not in tables:
        op.create_table(
            'snapshot_encryptions',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('source', sa.String(256), nullable=False),
            sa.Column('encryption_algorithm', sa.String(50), nullable=False, server_default='AES-256'),
            sa.Column('key_id', sa.String(100), nullable=True),
            sa.Column('pre_state_encrypted', sa.Text(), nullable=False),
            sa.Column('pre_state_iv', sa.String(100), nullable=False),
            sa.Column('post_state_encrypted', sa.Text(), nullable=True),
            sa.Column('post_state_iv', sa.String(100), nullable=True),
            sa.Column('rollback_plan', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('retention_days', sa.Integer(), nullable=False, server_default='7'),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_snapshot_encryptions_name', 'snapshot_encryptions', ['name'])
        op.create_index('idx_snapshot_encryptions_status', 'snapshot_encryptions', ['status'])
        op.create_index('idx_snapshot_encryptions_expires_at', 'snapshot_encryptions', ['expires_at'])

    # Create data_encryption_keys table
    if 'data_encryption_keys' not in tables:
        op.create_table(
            'data_encryption_keys',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('key_encrypted', sa.Text(), nullable=False),
            sa.Column('key_iv', sa.String(100), nullable=False),
            sa.Column('algorithm', sa.String(50), nullable=False, server_default='AES-256'),
            sa.Column('key_size', sa.Integer(), nullable=False, server_default='256'),
            sa.Column('purpose', sa.String(50), nullable=False),
            sa.Column('scope', sa.String(256), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('rotation_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('rotation_interval_days', sa.Integer(), nullable=True),
            sa.Column('last_rotated_at', sa.DateTime(), nullable=True),
            sa.Column('next_rotation_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_data_encryption_keys_name', 'data_encryption_keys', ['name'])
        op.create_index('idx_data_encryption_keys_status', 'data_encryption_keys', ['status'])
        op.create_index('idx_data_encryption_keys_purpose', 'data_encryption_keys', ['purpose'])

    # Create privacy_subjects table
    if 'privacy_subjects' not in tables:
        op.create_table(
            'privacy_subjects',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('subject_type', sa.String(50), nullable=False),
            sa.Column('email', sa.String(255), nullable=True),
            sa.Column('phone', sa.String(50), nullable=True),
            sa.Column('identifier', sa.String(255), nullable=True),
            sa.Column('consent_level', sa.String(20), nullable=False, server_default='partial'),
            sa.Column('consent_given_at', sa.DateTime(), nullable=True),
            sa.Column('consent_updated_at', sa.DateTime(), nullable=True),
            sa.Column('data_categories', sa.JSON(), nullable=True),
            sa.Column('processing_purposes', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_privacy_subjects_name', 'privacy_subjects', ['name'])
        op.create_index('idx_privacy_subjects_type', 'privacy_subjects', ['subject_type'])

    # Create compliance_policies table
    if 'compliance_policies' not in tables:
        op.create_table(
            'compliance_policies',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('framework', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('requirements', sa.JSON(), nullable=False),
            sa.Column('controls', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('last_audit_date', sa.DateTime(), nullable=True),
            sa.Column('next_audit_date', sa.DateTime(), nullable=True),
            sa.Column('audit_frequency_days', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_compliance_policies_name', 'compliance_policies', ['name'])
        op.create_index('idx_compliance_policies_framework', 'compliance_policies', ['framework'])
        op.create_index('idx_compliance_policies_status', 'compliance_policies', ['status'])

    # Create compliance_standards table
    if 'compliance_standards' not in tables:
        op.create_table(
            'compliance_standards',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('category', sa.String(50), nullable=False, server_default='general'),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('check_criteria', sa.JSON(), nullable=False),
            sa.Column('severity', sa.String(20), nullable=False, server_default='medium'),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_compliance_standards_name', 'compliance_standards', ['name'])
        op.create_index('idx_compliance_standards_category', 'compliance_standards', ['category'])
        op.create_index('idx_compliance_standards_status', 'compliance_standards', ['status'])

    # Create database_security_instances table
    if 'database_security_instances' not in tables:
        op.create_table(
            'database_security_instances',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('instance_type', sa.String(50), nullable=False),
            sa.Column('host', sa.String(256), nullable=False),
            sa.Column('port', sa.Integer(), nullable=True),
            sa.Column('encryption_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('ssl_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('audit_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('allowed_ips', sa.JSON(), nullable=True),
            sa.Column('allowed_users', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_database_security_instances_name', 'database_security_instances', ['name'])
        op.create_index('idx_database_security_instances_type', 'database_security_instances', ['instance_type'])
        op.create_index('idx_database_security_instances_status', 'database_security_instances', ['status'])

    # Create api_security_endpoints table
    if 'api_security_endpoints' not in tables:
        op.create_table(
            'api_security_endpoints',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('path', sa.String(256), nullable=False),
            sa.Column('method', sa.String(10), nullable=False),
            sa.Column('authentication_required', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('authorization_required', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('rate_limit_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('rate_limit_rule_id', sa.String(100), nullable=True),
            sa.Column('allowed_roles', sa.JSON(), nullable=True),
            sa.Column('allowed_permissions', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_api_security_endpoints_path', 'api_security_endpoints', ['path'])
        op.create_index('idx_api_security_endpoints_status', 'api_security_endpoints', ['status'])

    # Create input_validation_rules table
    if 'input_validation_rules' not in tables:
        op.create_table(
            'input_validation_rules',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('field', sa.String(128), nullable=False),
            sa.Column('validation_type', sa.String(50), nullable=False),
            sa.Column('validation_pattern', sa.String(500), nullable=True),
            sa.Column('min_length', sa.Integer(), nullable=True),
            sa.Column('max_length', sa.Integer(), nullable=True),
            sa.Column('min_value', sa.Float(), nullable=True),
            sa.Column('max_value', sa.Float(), nullable=True),
            sa.Column('allowed_values', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('error_code', sa.String(50), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_input_validation_rules_name', 'input_validation_rules', ['name'])
        op.create_index('idx_input_validation_rules_field', 'input_validation_rules', ['field'])
        op.create_index('idx_input_validation_rules_enabled', 'input_validation_rules', ['enabled'])

    # Create penetration_test_projects table
    if 'penetration_test_projects' not in tables:
        op.create_table(
            'penetration_test_projects',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('target', sa.String(256), nullable=False),
            sa.Column('test_type', sa.String(50), nullable=False),
            sa.Column('scope', sa.JSON(), nullable=True),
            sa.Column('methodology', sa.String(50), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
            sa.Column('start_date', sa.DateTime(), nullable=True),
            sa.Column('end_date', sa.DateTime(), nullable=True),
            sa.Column('findings', sa.JSON(), nullable=True),
            sa.Column('risk_score', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_penetration_test_projects_name', 'penetration_test_projects', ['name'])
        op.create_index('idx_penetration_test_projects_status', 'penetration_test_projects', ['status'])

    # Create security_tests table
    if 'security_tests' not in tables:
        op.create_table(
            'security_tests',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('test_type', sa.String(50), nullable=False),
            sa.Column('target', sa.String(256), nullable=True),
            sa.Column('parameters', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('results', sa.JSON(), nullable=True),
            sa.Column('vulnerabilities_found', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('critical_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('high_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('medium_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('low_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_security_tests_name', 'security_tests', ['name'])
        op.create_index('idx_security_tests_type', 'security_tests', ['test_type'])
        op.create_index('idx_security_tests_status', 'security_tests', ['status'])

    # Create vulnerability_tickets table
    if 'vulnerability_tickets' not in tables:
        op.create_table(
            'vulnerability_tickets',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('title', sa.String(128), nullable=False),
            sa.Column('cve_id', sa.String(50), nullable=True),
            sa.Column('severity', sa.String(20), nullable=False),
            sa.Column('cvss_score', sa.Float(), nullable=True),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('affected_components', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='open'),
            sa.Column('assigned_to', sa.String(50), nullable=True),
            sa.Column('fix_status', sa.String(20), nullable=True),
            sa.Column('fix_description', sa.Text(), nullable=True),
            sa.Column('detected_at', sa.DateTime(), nullable=False),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_vulnerability_tickets_title', 'vulnerability_tickets', ['title'])
        op.create_index('idx_vulnerability_tickets_severity', 'vulnerability_tickets', ['severity'])
        op.create_index('idx_vulnerability_tickets_status', 'vulnerability_tickets', ['status'])
        op.create_index('idx_vulnerability_tickets_cve_id', 'vulnerability_tickets', ['cve_id'])
        op.create_index('idx_vulnerability_tickets_detected_at', 'vulnerability_tickets', ['detected_at'])

    # Create threat_intelligence table
    if 'threat_intelligence' not in tables:
        op.create_table(
            'threat_intelligence',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('threat_type', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('indicators', sa.JSON(), nullable=True),
            sa.Column('source', sa.String(256), nullable=True),
            sa.Column('severity', sa.String(20), nullable=False, server_default='medium'),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('first_seen', sa.DateTime(), nullable=True),
            sa.Column('last_seen', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_threat_intelligence_name', 'threat_intelligence', ['name'])
        op.create_index('idx_threat_intelligence_type', 'threat_intelligence', ['threat_type'])
        op.create_index('idx_threat_intelligence_status', 'threat_intelligence', ['status'])

    # Create vulnerability_scans table
    if 'vulnerability_scans' not in tables:
        op.create_table(
            'vulnerability_scans',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('target', sa.String(256), nullable=False),
            sa.Column('scan_type', sa.String(50), nullable=False),
            sa.Column('parameters', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('results', sa.JSON(), nullable=True),
            sa.Column('vulnerabilities_found', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_vulnerability_scans_target', 'vulnerability_scans', ['target'])
        op.create_index('idx_vulnerability_scans_status', 'vulnerability_scans', ['status'])

    # Create audit_reports table
    if 'audit_reports' not in tables:
        op.create_table(
            'audit_reports',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('title', sa.String(128), nullable=False),
            sa.Column('report_type', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('findings', sa.JSON(), nullable=True),
            sa.Column('recommendations', sa.JSON(), nullable=True),
            sa.Column('scope', sa.JSON(), nullable=True),
            sa.Column('time_range_start', sa.DateTime(), nullable=True),
            sa.Column('time_range_end', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_audit_reports_title', 'audit_reports', ['title'])
        op.create_index('idx_audit_reports_type', 'audit_reports', ['report_type'])
        op.create_index('idx_audit_reports_status', 'audit_reports', ['status'])

    # Create security_operation_records table
    if 'security_operation_records' not in tables:
        op.create_table(
            'security_operation_records',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('operation', sa.String(100), nullable=False),
            sa.Column('operation_type', sa.String(50), nullable=False),
            sa.Column('target_resource', sa.String(256), nullable=True),
            sa.Column('parameters', sa.JSON(), nullable=True),
            sa.Column('executor', sa.String(50), nullable=True),
            sa.Column('result', sa.String(20), nullable=False),
            sa.Column('output', sa.Text(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('duration_ms', sa.Integer(), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_security_operation_records_operation', 'security_operation_records', ['operation'])
        op.create_index('idx_security_operation_records_timestamp', 'security_operation_records', ['timestamp'])

    # Create command_rewrite_rules table
    if 'command_rewrite_rules' not in tables:
        op.create_table(
            'command_rewrite_rules',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('pattern', sa.String(256), nullable=False),
            sa.Column('replacement', sa.String(256), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_command_rewrite_rules_pattern', 'command_rewrite_rules', ['pattern'])
        op.create_index('idx_command_rewrite_rules_enabled', 'command_rewrite_rules', ['enabled'])

    # Create command_guard_rules table
    if 'command_guard_rules' not in tables:
        op.create_table(
            'command_guard_rules',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('command', sa.String(256), nullable=False),
            sa.Column('pattern', sa.String(256), nullable=False),
            sa.Column('severity', sa.String(20), nullable=False, server_default='high'),
            sa.Column('action', sa.String(20), nullable=False, server_default='block'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('trigger_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )
        op.create_index('idx_command_guard_rules_command', 'command_guard_rules', ['command'])
        op.create_index('idx_command_guard_rules_enabled', 'command_guard_rules', ['enabled'])


def downgrade():
    """Remove Security Management-related tables"""

    # Drop indexes first (in reverse order of creation)
    indexes_to_drop = [
        ('idx_command_guard_rules_enabled', 'command_guard_rules'),
        ('idx_command_guard_rules_command', 'command_guard_rules'),
        ('idx_command_rewrite_rules_enabled', 'command_rewrite_rules'),
        ('idx_command_rewrite_rules_pattern', 'command_rewrite_rules'),
        ('idx_security_operation_records_timestamp', 'security_operation_records'),
        ('idx_security_operation_records_operation', 'security_operation_records'),
        ('idx_audit_reports_status', 'audit_reports'),
        ('idx_audit_reports_type', 'audit_reports'),
        ('idx_audit_reports_title', 'audit_reports'),
        ('idx_vulnerability_scans_status', 'vulnerability_scans'),
        ('idx_vulnerability_scans_target', 'vulnerability_scans'),
        ('idx_threat_intelligence_status', 'threat_intelligence'),
        ('idx_threat_intelligence_type', 'threat_intelligence'),
        ('idx_threat_intelligence_name', 'threat_intelligence'),
        ('idx_vulnerability_tickets_detected_at', 'vulnerability_tickets'),
        ('idx_vulnerability_tickets_cve_id', 'vulnerability_tickets'),
        ('idx_vulnerability_tickets_status', 'vulnerability_tickets'),
        ('idx_vulnerability_tickets_severity', 'vulnerability_tickets'),
        ('idx_vulnerability_tickets_title', 'vulnerability_tickets'),
        ('idx_security_tests_status', 'security_tests'),
        ('idx_security_tests_type', 'security_tests'),
        ('idx_security_tests_name', 'security_tests'),
        ('idx_penetration_test_projects_status', 'penetration_test_projects'),
        ('idx_penetration_test_projects_name', 'penetration_test_projects'),
        ('idx_input_validation_rules_enabled', 'input_validation_rules'),
        ('idx_input_validation_rules_field', 'input_validation_rules'),
        ('idx_input_validation_rules_name', 'input_validation_rules'),
        ('idx_api_security_endpoints_status', 'api_security_endpoints'),
        ('idx_api_security_endpoints_path', 'api_security_endpoints'),
        ('idx_database_security_instances_status', 'database_security_instances'),
        ('idx_database_security_instances_type', 'database_security_instances'),
        ('idx_database_security_instances_name', 'database_security_instances'),
        ('idx_compliance_standards_status', 'compliance_standards'),
        ('idx_compliance_standards_category', 'compliance_standards'),
        ('idx_compliance_standards_name', 'compliance_standards'),
        ('idx_compliance_policies_status', 'compliance_policies'),
        ('idx_compliance_policies_framework', 'compliance_policies'),
        ('idx_compliance_policies_name', 'compliance_policies'),
        ('idx_privacy_subjects_type', 'privacy_subjects'),
        ('idx_privacy_subjects_name', 'privacy_subjects'),
        ('idx_data_encryption_keys_purpose', 'data_encryption_keys'),
        ('idx_data_encryption_keys_status', 'data_encryption_keys'),
        ('idx_data_encryption_keys_name', 'data_encryption_keys'),
        ('idx_snapshot_encryptions_expires_at', 'snapshot_encryptions'),
        ('idx_snapshot_encryptions_status', 'snapshot_encryptions'),
        ('idx_snapshot_encryptions_name', 'snapshot_encryptions'),
        ('idx_https_certificates_expires_at', 'https_certificates'),
        ('idx_https_certificates_status', 'https_certificates'),
        ('idx_https_certificates_domain', 'https_certificates'),
        ('idx_rate_limit_rules_enabled', 'rate_limit_rules'),
        ('idx_rate_limit_rules_endpoint', 'rate_limit_rules'),
        ('idx_rate_limit_rules_name', 'rate_limit_rules'),
        ('idx_rbac_roles_status', 'rbac_roles'),
        ('idx_rbac_roles_name', 'rbac_roles'),
        ('idx_abac_policies_enabled', 'abac_policies'),
        ('idx_abac_policies_name', 'abac_policies'),
        ('idx_mfa_methods_enabled', 'mfa_methods'),
        ('idx_mfa_methods_type', 'mfa_methods'),
        ('idx_security_keys_expires_at', 'security_keys'),
        ('idx_security_keys_status', 'security_keys'),
        ('idx_security_keys_type', 'security_keys'),
        ('idx_security_keys_name', 'security_keys'),
    ]

    for index_name, table_name in indexes_to_drop:
        try:
            op.drop_index(index_name, table_name)
        except Exception:
            pass  # Index may not exist

    # Drop tables (in reverse order of creation)
    tables_to_drop = [
        'command_guard_rules',
        'command_rewrite_rules',
        'security_operation_records',
        'audit_reports',
        'vulnerability_scans',
        'threat_intelligence',
        'vulnerability_tickets',
        'security_tests',
        'penetration_test_projects',
        'input_validation_rules',
        'api_security_endpoints',
        'database_security_instances',
        'compliance_standards',
        'compliance_policies',
        'privacy_subjects',
        'data_encryption_keys',
        'snapshot_encryptions',
        'https_certificates',
        'rate_limit_rules',
        'rbac_roles',
        'abac_policies',
        'mfa_methods',
        'security_keys',
    ]

    for table_name in tables_to_drop:
        try:
            op.drop_table(table_name)
        except Exception:
            pass  # Table may not exist

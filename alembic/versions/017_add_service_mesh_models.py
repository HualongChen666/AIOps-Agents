# -*- coding: utf-8 -*-
"""
Add Service Mesh Models

This migration adds Service Mesh-related tables to support service mesh management:
- mesh_configurations: Stores service mesh configuration (Istio, Linkerd, Consul)
- traffic_rules: Stores traffic routing rules for service mesh
- security_policies: Stores security policies (mTLS, JWT, authorization)
- observability_configs: Stores observability configuration (tracing, metrics, logging)
- policies: Stores generic policies for service mesh

This model supports the Service Mesh Advanced API endpoints:
- GET/POST/PATCH/DELETE /api/v1/service-mesh/configurations
- GET/POST/PATCH/DELETE /api/v1/service-mesh/traffic
- GET/POST/PATCH/DELETE /api/v1/service-mesh/security
- GET/POST/PATCH/DELETE /api/v1/service-mesh/observability
- GET/POST/PATCH/DELETE /api/v1/service-mesh/policies
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    """Add Service Mesh-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create mesh_configurations table
    if 'mesh_configurations' not in tables:
        op.create_table(
            'mesh_configurations',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('mesh_type', sa.String(50), nullable=False),
            sa.Column('namespace', sa.String(100), nullable=False),
            sa.Column('profile', sa.String(50), nullable=False),
            sa.Column('auto_injection_enabled', sa.Boolean(), nullable=False),
            sa.Column('mtls_enabled', sa.Boolean(), nullable=False),
            sa.Column('resource_limits', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False),
            sa.Column('mesh_id', sa.String(100), nullable=False),
            sa.Column('config_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

        # Create indexes for mesh_configurations
        op.create_index('idx_mesh_configurations_name', 'mesh_configurations', ['name'])
        op.create_index('idx_mesh_configurations_mesh_type', 'mesh_configurations', ['mesh_type'])
        op.create_index('idx_mesh_configurations_status', 'mesh_configurations', ['status'])
        op.create_index('idx_mesh_configurations_mesh_id', 'mesh_configurations', ['mesh_id'])

    # Create traffic_rules table
    if 'traffic_rules' not in tables:
        op.create_table(
            'traffic_rules',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('service_name', sa.String(200), nullable=False),
            sa.Column('match_conditions', sa.JSON(), nullable=False),
            sa.Column('destination', sa.JSON(), nullable=False),
            sa.Column('weight', sa.Integer(), nullable=False),
            sa.Column('timeout_seconds', sa.Integer(), nullable=False),
            sa.Column('retry_policy', sa.JSON(), nullable=True),
            sa.Column('fault_injection', sa.JSON(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.Column('rule_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

        # Create indexes for traffic_rules
        op.create_index('idx_traffic_rules_name', 'traffic_rules', ['name'])
        op.create_index('idx_traffic_rules_service_name', 'traffic_rules', ['service_name'])
        op.create_index('idx_traffic_rules_enabled', 'traffic_rules', ['enabled'])

    # Create security_policies table
    if 'security_policies' not in tables:
        op.create_table(
            'security_policies',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('policy_type', sa.String(50), nullable=False),
            sa.Column('target_service', sa.String(200), nullable=False),
            sa.Column('mtls_mode', sa.String(20), nullable=False),
            sa.Column('allowed_principals', sa.JSON(), nullable=True),
            sa.Column('denied_principals', sa.JSON(), nullable=True),
            sa.Column('jwt_validation', sa.JSON(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.Column('policy_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

        # Create indexes for security_policies
        op.create_index('idx_security_policies_name', 'security_policies', ['name'])
        op.create_index('idx_security_policies_policy_type', 'security_policies', ['policy_type'])
        op.create_index('idx_security_policies_target_service', 'security_policies', ['target_service'])
        op.create_index('idx_security_policies_enabled', 'security_policies', ['enabled'])

    # Create observability_configs table
    if 'observability_configs' not in tables:
        op.create_table(
            'observability_configs',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('tracing_enabled', sa.Boolean(), nullable=False),
            sa.Column('metrics_enabled', sa.Boolean(), nullable=False),
            sa.Column('access_logging_enabled', sa.Boolean(), nullable=False),
            sa.Column('sampling_rate', sa.Float(), nullable=False),
            sa.Column('prometheus_enabled', sa.Boolean(), nullable=False),
            sa.Column('grafana_enabled', sa.Boolean(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.Column('config_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

        # Create indexes for observability_configs
        op.create_index('idx_observability_configs_name', 'observability_configs', ['name'])
        op.create_index('idx_observability_configs_enabled', 'observability_configs', ['enabled'])

    # Create policies table
    if 'policies' not in tables:
        op.create_table(
            'policies',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('policy_type', sa.String(50), nullable=False),
            sa.Column('target_service', sa.String(200), nullable=False),
            sa.Column('rules', sa.JSON(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.Column('policy_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

        # Create indexes for policies
        op.create_index('idx_policies_name', 'policies', ['name'])
        op.create_index('idx_policies_policy_type', 'policies', ['policy_type'])
        op.create_index('idx_policies_target_service', 'policies', ['target_service'])
        op.create_index('idx_policies_enabled', 'policies', ['enabled'])


def downgrade():
    """Remove Service Mesh-related tables"""

    # Check if tables exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'policies' in tables:
        # Drop indexes first
        try:
            op.drop_index('idx_policies_enabled', 'policies')
        except Exception:
            pass
        try:
            op.drop_index('idx_policies_target_service', 'policies')
        except Exception:
            pass
        try:
            op.drop_index('idx_policies_policy_type', 'policies')
        except Exception:
            pass
        try:
            op.drop_index('idx_policies_name', 'policies')
        except Exception:
            pass
        op.drop_table('policies')

    if 'observability_configs' in tables:
        try:
            op.drop_index('idx_observability_configs_enabled', 'observability_configs')
        except Exception:
            pass
        try:
            op.drop_index('idx_observability_configs_name', 'observability_configs')
        except Exception:
            pass
        op.drop_table('observability_configs')

    if 'security_policies' in tables:
        try:
            op.drop_index('idx_security_policies_enabled', 'security_policies')
        except Exception:
            pass
        try:
            op.drop_index('idx_security_policies_target_service', 'security_policies')
        except Exception:
            pass
        try:
            op.drop_index('idx_security_policies_policy_type', 'security_policies')
        except Exception:
            pass
        try:
            op.drop_index('idx_security_policies_name', 'security_policies')
        except Exception:
            pass
        op.drop_table('security_policies')

    if 'traffic_rules' in tables:
        try:
            op.drop_index('idx_traffic_rules_enabled', 'traffic_rules')
        except Exception:
            pass
        try:
            op.drop_index('idx_traffic_rules_service_name', 'traffic_rules')
        except Exception:
            pass
        try:
            op.drop_index('idx_traffic_rules_name', 'traffic_rules')
        except Exception:
            pass
        op.drop_table('traffic_rules')

    if 'mesh_configurations' in tables:
        try:
            op.drop_index('idx_mesh_configurations_mesh_id', 'mesh_configurations')
        except Exception:
            pass
        try:
            op.drop_index('idx_mesh_configurations_status', 'mesh_configurations')
        except Exception:
            pass
        try:
            op.drop_index('idx_mesh_configurations_mesh_type', 'mesh_configurations')
        except Exception:
            pass
        try:
            op.drop_index('idx_mesh_configurations_name', 'mesh_configurations')
        except Exception:
            pass
        op.drop_table('mesh_configurations')

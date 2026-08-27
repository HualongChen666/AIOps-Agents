"""Add AI advanced models

Revision ID: 007_add_ai_advanced_models
Revises: 006_add_change_management_models
Create Date: 2026-08-26 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_fine_tuning_jobs table
    op.create_table(
        'ai_fine_tuning_jobs',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('dataset', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('job_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_fine_tuning_jobs_status', 'status'),
    )

    # Create ai_runbooks table
    op.create_table(
        'ai_runbooks',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('steps', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('runbook_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create ai_analysis_reports table
    op.create_table(
        'ai_analysis_reports',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('results', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('report_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_analysis_reports_type', 'analysis_type'),
    )

    # Create ai_dsl_definitions table
    op.create_table(
        'ai_dsl_definitions',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('dsl_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create ai_executions table
    op.create_table(
        'ai_executions',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('dsl_id', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_executions_dsl_id', 'dsl_id'),
        sa.Index('idx_ai_executions_status', 'status'),
    )

    # Create ai_workflows table
    op.create_table(
        'ai_workflows',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('nodes', sa.JSON(), nullable=False),
        sa.Column('edges', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('workflow_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_workflows_status', 'status'),
    )

    # Create ai_deep_learning_models table
    op.create_table(
        'ai_deep_learning_models',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('architecture', sa.String(50), nullable=False),
        sa.Column('performance_metrics', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('model_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create ai_advanced_features table
    op.create_table(
        'ai_advanced_features',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('feature_name', sa.String(255), nullable=False),
        sa.Column('feature_type', sa.String(50), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='enabled'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('feature_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_advanced_features_status', 'status'),
    )

    # Create ai_feedbacks table
    op.create_table(
        'ai_feedbacks',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('feedback_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_feedbacks_type', 'feedback_type'),
    )

    # Create ai_document_indexes table
    op.create_table(
        'ai_document_indexes',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('index_name', sa.String(255), nullable=False),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('index_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create ai_patterns table
    op.create_table(
        'ai_patterns',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('pattern_name', sa.String(255), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('pattern_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('pattern_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_patterns_type', 'pattern_type'),
    )

    # Create ai_topology_analyses table
    op.create_table(
        'ai_topology_analyses',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('results', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('topology_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_topology_analyses_type', 'analysis_type'),
    )

    # Create ai_root_cause_analyses table
    op.create_table(
        'ai_root_cause_analyses',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('incident_id', sa.String(50), nullable=False),
        sa.Column('root_cause', sa.Text(), nullable=False),
        sa.Column('contributing_factors', sa.JSON(), nullable=False),
        sa.Column('recommended_actions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('rca_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_root_cause_analyses_incident', 'incident_id'),
    )

    # Create ai_graph_nodes table
    op.create_table(
        'ai_graph_nodes',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('node_type', sa.String(50), nullable=False),
        sa.Column('node_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('node_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_graph_nodes_type', 'node_type'),
    )

    # Create ai_knowledge_bases table
    op.create_table(
        'ai_knowledge_bases',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('kb_name', sa.String(255), nullable=False),
        sa.Column('kb_type', sa.String(50), nullable=False),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('kb_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_knowledge_bases_type', 'kb_type'),
    )

    # Create ai_load_balancer_configs table
    op.create_table(
        'ai_load_balancer_configs',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('config_name', sa.String(255), nullable=False),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('targets', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('config_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_load_balancer_configs_status', 'status'),
    )

    # Create ai_cost_suggestions table
    op.create_table(
        'ai_cost_suggestions',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('suggestion_type', sa.String(50), nullable=False),
        sa.Column('potential_savings', sa.Float(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('cost_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_cost_suggestions_status', 'status'),
    )

    # Create ai_routing_rules table
    op.create_table(
        'ai_routing_rules',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('condition', sa.JSON(), nullable=False),
        sa.Column('action', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('rule_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ai_routing_rules_status', 'status'),
    )

def downgrade():
    # Drop tables in reverse order
    op.drop_table('ai_routing_rules')
    op.drop_table('ai_cost_suggestions')
    op.drop_table('ai_load_balancer_configs')
    op.drop_table('ai_knowledge_bases')
    op.drop_table('ai_graph_nodes')
    op.drop_table('ai_root_cause_analyses')
    op.drop_table('ai_topology_analyses')
    op.drop_table('ai_patterns')
    op.drop_table('ai_document_indexes')
    op.drop_table('ai_feedbacks')
    op.drop_table('ai_advanced_features')
    op.drop_table('ai_deep_learning_models')
    op.drop_table('ai_workflows')
    op.drop_table('ai_executions')
    op.drop_table('ai_dsl_definitions')
    op.drop_table('ai_analysis_reports')
    op.drop_table('ai_runbooks')
    op.drop_table('ai_fine_tuning_jobs')

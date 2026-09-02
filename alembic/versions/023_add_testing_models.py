# -*- coding: utf-8 -*-
"""
Add Testing Models

This migration adds Testing-related tables to support testing features:
- test_suites: Test suite management
- test_cases: Test case storage
- test_reports: Test report storage
- test_coverages: Test coverage tracking
- coverage_thresholds: Coverage threshold configuration
- automation_jobs: Automation job management
- cicd_pipeline_configs: CI/CD pipeline configuration
- test_notification_configs: Test notification configuration

This model supports the Testing API endpoints:
- Test Automation: GET/POST /api/test-automation/*
- Test Coverage: GET/POST /api/test-coverage/*
- Test Framework: GET/POST /api/test-framework/*
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    """Add Testing-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create testing_suites table
    if 'testing_suites' not in tables:
        op.create_table(
            'testing_suites',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('suite_id', sa.String(100), nullable=False),
            sa.Column('suite_name', sa.String(200), nullable=False),
            sa.Column('test_type', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('test_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('coverage_target', sa.Float(), nullable=False, server_default='80.0'),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('suite_id'),
            sa.Index('idx_testing_suites_suite_id', 'suite_id'),
            sa.Index('idx_testing_suites_test_type', 'test_type'),
            sa.Index('idx_testing_suites_status', 'status'),
        )

    # Create testing_cases table
    if 'testing_cases' not in tables:
        op.create_table(
            'testing_cases',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('test_id', sa.String(100), nullable=False),
            sa.Column('suite_id', sa.String(100), nullable=False),
            sa.Column('test_name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('test_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('executed_at', sa.DateTime(), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('test_id'),
            sa.Index('idx_testing_cases_test_id', 'test_id'),
            sa.Index('idx_testing_cases_suite_id', 'suite_id'),
            sa.Index('idx_testing_cases_test_type', 'test_type'),
            sa.Index('idx_testing_cases_status', 'status'),
        )

    # Create testing_reports table
    if 'testing_reports' not in tables:
        op.create_table(
            'testing_reports',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('report_id', sa.String(100), nullable=False),
            sa.Column('suite_id', sa.String(100), nullable=False),
            sa.Column('test_type', sa.String(50), nullable=False),
            sa.Column('start_time', sa.DateTime(), nullable=False),
            sa.Column('end_time', sa.DateTime(), nullable=True),
            sa.Column('total_tests', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('passed_tests', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failed_tests', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('skipped_tests', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('coverage', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('duration_sec', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('report_id'),
            sa.Index('idx_testing_reports_report_id', 'report_id'),
            sa.Index('idx_testing_reports_suite_id', 'suite_id'),
            sa.Index('idx_testing_reports_test_type', 'test_type'),
            sa.Index('idx_testing_reports_start_time', 'start_time'),
        )

    # Create testing_coverages table
    if 'testing_coverages' not in tables:
        op.create_table(
            'testing_coverages',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('module_id', sa.String(100), nullable=False),
            sa.Column('module_name', sa.String(200), nullable=False),
            sa.Column('module_type', sa.String(50), nullable=False),
            sa.Column('total_lines', sa.Integer(), nullable=False),
            sa.Column('covered_lines', sa.Integer(), nullable=False),
            sa.Column('coverage_percentage', sa.Float(), nullable=False),
            sa.Column('coverage_level', sa.String(50), nullable=False),
            sa.Column('last_updated', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('module_id'),
            sa.Index('idx_testing_coverages_module_id', 'module_id'),
            sa.Index('idx_testing_coverages_module_type', 'module_type'),
            sa.Index('idx_testing_coverages_coverage_level', 'coverage_level'),
        )

    # Create testing_coverage_thresholds table
    if 'testing_coverage_thresholds' not in tables:
        op.create_table(
            'testing_coverage_thresholds',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('module_type', sa.String(50), nullable=False),
            sa.Column('minimum_coverage', sa.Float(), nullable=False),
            sa.Column('target_coverage', sa.Float(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('module_type'),
            sa.Index('idx_testing_coverage_thresholds_module_type', 'module_type'),
        )

    # Create testing_automation_jobs table
    if 'testing_automation_jobs' not in tables:
        op.create_table(
            'testing_automation_jobs',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('job_id', sa.String(100), nullable=False),
            sa.Column('job_name', sa.String(200), nullable=False),
            sa.Column('job_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='idle'),
            sa.Column('trigger_type', sa.String(50), nullable=False, server_default='manual'),
            sa.Column('start_time', sa.DateTime(), nullable=True),
            sa.Column('end_time', sa.DateTime(), nullable=True),
            sa.Column('duration_sec', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('job_id'),
            sa.Index('idx_testing_automation_jobs_job_id', 'job_id'),
            sa.Index('idx_testing_automation_jobs_job_type', 'job_type'),
            sa.Index('idx_testing_automation_jobs_status', 'status'),
            sa.Index('idx_testing_automation_jobs_start_time', 'start_time'),
        )

    # Create testing_cicd_pipeline_configs table
    if 'testing_cicd_pipeline_configs' not in tables:
        op.create_table(
            'testing_cicd_pipeline_configs',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('config_id', sa.String(100), nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('platform', sa.String(50), nullable=False),
            sa.Column('config_content', sa.Text(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('config_id'),
            sa.Index('idx_testing_cicd_pipeline_configs_config_id', 'config_id'),
            sa.Index('idx_testing_cicd_pipeline_configs_platform', 'platform'),
            sa.Index('idx_testing_cicd_pipeline_configs_enabled', 'enabled'),
        )

    # Create testing_notification_configs table
    if 'testing_notification_configs' not in tables:
        op.create_table(
            'testing_notification_configs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('config_name', sa.String(200), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('on_success', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('on_failure', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('channels', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('config_name'),
            sa.Index('idx_testing_notification_configs_name', 'config_name'),
        )

    # Insert default coverage thresholds
    if 'testing_coverage_thresholds' in tables:
        op.execute("""
            INSERT OR IGNORE INTO testing_coverage_thresholds (module_type, minimum_coverage, target_coverage, created_at, updated_at)
            VALUES
                ('core', 70.0, 80.0, datetime('now'), datetime('now')),
                ('integration', 65.0, 75.0, datetime('now'), datetime('now')),
                ('ai', 60.0, 70.0, datetime('now'), datetime('now')),
                ('api', 75.0, 85.0, datetime('now'), datetime('now'))
        """)

    # Insert default notification config
    if 'testing_notification_configs' in tables:
        op.execute("""
            INSERT OR IGNORE INTO testing_notification_configs (config_name, enabled, on_success, on_failure, channels, created_at, updated_at)
            VALUES ('default', 0, 1, 1, '["email", "slack"]', datetime('now'), datetime('now'))
        """)


def downgrade():
    """Remove Testing-related tables"""

    # Drop tables in reverse order of creation (to handle foreign key constraints)
    op.drop_table('testing_notification_configs')
    op.drop_table('testing_cicd_pipeline_configs')
    op.drop_table('testing_automation_jobs')
    op.drop_table('testing_coverage_thresholds')
    op.drop_table('testing_coverages')
    op.drop_table('testing_reports')
    op.drop_table('testing_cases')
    op.drop_table('testing_suites')

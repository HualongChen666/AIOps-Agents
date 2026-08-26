"""Add AI, Compliance, and Builder models.

Revision ID: 002
Revises: 001
Create Date: 2026-08-26 08:59:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AI Functionality Models
    op.create_table(
        "fine_tuning_jobs",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("dataset_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("parameters", sa.JSON, nullable=True),
        sa.Column("metrics", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(50), nullable=True),
    )
    op.create_index("idx_fine_tuning_jobs_status", "fine_tuning_jobs", ["status"])
    op.create_index("idx_fine_tuning_jobs_model_name", "fine_tuning_jobs", ["model_name"])
    op.create_index("idx_fine_tuning_jobs_created_at", "fine_tuning_jobs", ["created_at"])

    op.create_table(
        "training_datasets",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("data_type", sa.String(50), nullable=False),
        sa.Column("size", sa.Integer, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("extra_data", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(50), nullable=True),
    )
    op.create_index("idx_training_datasets_data_type", "training_datasets", ["data_type"])
    op.create_index("idx_training_datasets_created_at", "training_datasets", ["created_at"])

    op.create_table(
        "model_deployments",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("endpoint", sa.String(500), nullable=True),
        sa.Column("config", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deployed_by", sa.String(50), nullable=True),
    )
    op.create_index("idx_model_deployments_environment", "model_deployments", ["environment"])
    op.create_index("idx_model_deployments_status", "model_deployments", ["status"])
    op.create_index("idx_model_deployments_model_name", "model_deployments", ["model_name"])

    # Compliance Audit Models
    op.create_table(
        "compliance_audits",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("audit_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("scope", sa.JSON, nullable=True),
        sa.Column("findings", sa.JSON, nullable=True),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(50), nullable=True),
    )
    op.create_index("idx_compliance_audits_type", "compliance_audits", ["audit_type"])
    op.create_index("idx_compliance_audits_status", "compliance_audits", ["status"])
    op.create_index("idx_compliance_audits_scheduled_date", "compliance_audits", ["scheduled_date"])

    # Builder Models
    op.create_table(
        "builder_templates",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("template_data", sa.JSON, nullable=False),
        sa.Column("components", sa.JSON, nullable=True),
        sa.Column("is_public", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(50), nullable=True),
    )
    op.create_index("idx_builder_templates_category", "builder_templates", ["category"])
    op.create_index("idx_builder_templates_is_public", "builder_templates", ["is_public"])

    op.create_table(
        "builder_projects",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("template_id", sa.String(100), nullable=True),
        sa.Column("project_data", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(50), nullable=True),
    )
    op.create_index("idx_builder_projects_status", "builder_projects", ["status"])
    op.create_index("idx_builder_projects_template_id", "builder_projects", ["template_id"])

    op.create_table(
        "builder_components",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("component_type", sa.String(50), nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("properties", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(50), nullable=True),
    )
    op.create_index("idx_builder_components_type", "builder_components", ["component_type"])


def downgrade() -> None:
    op.drop_index("idx_builder_components_type", table_name="builder_components")
    op.drop_table("builder_components")
    op.drop_index("idx_builder_projects_template_id", table_name="builder_projects")
    op.drop_index("idx_builder_projects_status", table_name="builder_projects")
    op.drop_table("builder_projects")
    op.drop_index("idx_builder_templates_is_public", table_name="builder_templates")
    op.drop_index("idx_builder_templates_category", table_name="builder_templates")
    op.drop_table("builder_templates")
    op.drop_index("idx_compliance_audits_scheduled_date", table_name="compliance_audits")
    op.drop_index("idx_compliance_audits_status", table_name="compliance_audits")
    op.drop_index("idx_compliance_audits_type", table_name="compliance_audits")
    op.drop_table("compliance_audits")
    op.drop_index("idx_model_deployments_model_name", table_name="model_deployments")
    op.drop_index("idx_model_deployments_status", table_name="model_deployments")
    op.drop_index("idx_model_deployments_environment", table_name="model_deployments")
    op.drop_table("model_deployments")
    op.drop_index("idx_training_datasets_created_at", table_name="training_datasets")
    op.drop_index("idx_training_datasets_data_type", table_name="training_datasets")
    op.drop_table("training_datasets")
    op.drop_index("idx_fine_tuning_jobs_created_at", table_name="fine_tuning_jobs")
    op.drop_index("idx_fine_tuning_jobs_model_name", table_name="fine_tuning_jobs")
    op.drop_index("idx_fine_tuning_jobs_status", table_name="fine_tuning_jobs")
    op.drop_table("fine_tuning_jobs")

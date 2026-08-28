# -*- coding: utf-8 -*-
"""
Initialize database tables for testing
"""

from core.database import engine, Base
from core.models import (
    ServiceMonitorAlertDB,
    ServiceMonitorDashboardDB,
    SLODefinitionDB,
    SLOObjectiveDB,
    SLOAlertDB,
    TenantConfigDB,
    TenantSettingsDB,
    TenantMemberDB,
    TestSuiteDB,
    TestExecutionDB,
    TestCoverageReportDB,
)

# Create all tables
Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")

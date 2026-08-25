# -*- coding: utf-8 -*-
"""
初始化高级功能数据库表
"""

from core.database import Base, engine
from core.models import (
    PriorityRule,
    PriorityScore,
    PriorityHistory,
    RealtimeStream,
    RealtimeEvent,
    RealtimeSubscription,
    RealtimeWebhook,
    RootCauseHypothesis,
    RootCauseExperiment,
    RootCauseEvidence,
    RootCauseConclusion,
)

if __name__ == "__main__":
    print("Creating advanced feature database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

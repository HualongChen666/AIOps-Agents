# -*- coding: utf-8 -*-
"""
Migration script for AIFusionConfigDB table

This script creates the ai_fusion_configs table in the database.
Run this after adding the AIFusionConfigDB model to core/models.py.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine

def migrate():
    """Create the ai_fusion_configs table"""
    with engine.connect() as conn:
        # Check if table already exists (SQLite specific)
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_fusion_configs'"
        ))
        exists = result.fetchone()

        if exists:
            print("Table ai_fusion_configs already exists. Skipping migration.")
            return

        # Create table
        conn.execute(text("""
            CREATE TABLE ai_fusion_configs (
                id VARCHAR(50) PRIMARY KEY NOT NULL,
                config_name VARCHAR(255) NOT NULL,
                fusion_strategy VARCHAR(50) NOT NULL,
                sources JSON NOT NULL,
                weights JSON,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                config_metadata JSON
            )
        """))

        # Create index
        conn.execute(text("""
            CREATE INDEX idx_ai_fusion_configs_status ON ai_fusion_configs (status)
        """))

        conn.commit()
        print("Successfully created ai_fusion_configs table and index.")

if __name__ == "__main__":
    migrate()

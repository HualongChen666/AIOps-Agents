# -*- coding: utf-8 -*-
"""
PostgreSQL Storage Module for AIOps Platform
Provides ACID-compliant relational storage for metadata, policies, and configuration
"""

from .storage import PostgreSQLStorage

__all__ = ["PostgreSQLStorage"]

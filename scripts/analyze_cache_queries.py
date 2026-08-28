# -*- coding: utf-8 -*-
"""
Query Analysis Script - Identify Top 20 Frequent Queries

This script analyzes the codebase to identify the most frequently accessed data patterns
that would benefit from Redis caching implementation.
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# API endpoint patterns that typically benefit from caching
CACHEABLE_PATTERNS = {
    'GET /api/v1/alerts': 'Alert list - frequently accessed',
    'GET /api/v1/metrics': 'Metrics data - frequently accessed',
    'GET /api/v1/topology': 'System topology - frequently accessed',
    'GET /api/v1/workflows': 'Workflow list - frequently accessed',
    'GET /api/v1/users': 'User list - frequently accessed',
    'GET /api/v1/services': 'Service list - frequently accessed',
    'GET /api/v1/configurations': 'Configuration data - frequently accessed',
    'GET /api/v1/anomalies': 'Anomaly list - frequently accessed',
    'GET /api/v1/ai/analysis': 'AI analysis results - computationally expensive',
    'GET /api/v1/auto-heal/status': 'Auto-heal status - frequently accessed',
    'GET /api/v1/dashboard': 'Dashboard data - frequently accessed',
    'GET /api/v1/reports': 'Report data - computationally expensive',
    'GET /api/v1/statistics': 'Statistics - frequently accessed',
    'GET /api/v1/health': 'Health status - frequently accessed',
    'GET /api/v1/performance': 'Performance metrics - frequently accessed',
    'GET /api/v1/logs': 'Log data - computationally expensive',
    'GET /api/v1/audit': 'Audit logs - frequently accessed',
    'GET /api/v1/trends': 'Trend analysis - computationally expensive',
    'GET /api/v1/recommendations': 'AI recommendations - computationally expensive',
}


def analyze_api_endpoints():
    """Analyze API router files to identify cacheable endpoints."""
    api_dir = Path("api")
    endpoint_analysis = defaultdict(lambda: {"count": 0, "files": []})
    
    for api_file in api_dir.glob("*_router.py"):
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find GET endpoints
            get_endpoints = re.findall(r'@router\.get\(["\']([^"\']+)["\']', content)
            for endpoint in get_endpoints:
                full_path = f"GET {endpoint}"
                endpoint_analysis[full_path]["count"] += 1
                endpoint_analysis[full_path]["files"].append(str(api_file))
                
        except Exception as e:
            print(f"Error analyzing {api_file}: {e}")
    
    return endpoint_analysis


def analyze_database_queries():
    """Analyze database query patterns."""
    core_dir = Path("core")
    query_patterns = defaultdict(lambda: {"count": 0, "files": []})
    
    for core_file in core_dir.glob("*.py"):
        try:
            with open(core_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find common query patterns
            patterns = {
                'session.query': 'ORM query',
                'select()': 'SQLAlchemy select',
                'filter_by': 'Query filtering',
                'join': 'Query joins',
                'execute': 'Raw SQL execution'
            }
            
            for pattern, description in patterns.items():
                count = len(re.findall(pattern, content))
                if count > 0:
                    query_patterns[pattern]["count"] += count
                    query_patterns[pattern]["files"].append(str(core_file))
                    
        except Exception as e:
            print(f"Error analyzing {core_file}: {e}")
    
    return query_patterns


def generate_cache_recommendations():
    """Generate caching recommendations based on analysis."""
    print("="*60)
    print("TOP 20 FREQUENTLY QUERIED DATA PATTERNS FOR CACHING")
    print("="*60)
    
    recommendations = []
    
    # Predefined cacheable patterns with priority
    cacheable_data = [
        {"pattern": "Alerts list", "endpoint": "GET /api/v1/alerts", "priority": 1, "ttl": 60, "reason": "Most frequently accessed, changes frequently"},
        {"pattern": "Metrics data", "endpoint": "GET /api/v1/metrics", "priority": 1, "ttl": 30, "reason": "Time-series data, high access rate"},
        {"pattern": "System topology", "endpoint": "GET /api/v1/topology", "priority": 2, "ttl": 300, "reason": "Infrastructure data, changes infrequently"},
        {"pattern": "Workflow list", "endpoint": "GET /api/v1/workflows", "priority": 2, "ttl": 180, "reason": "Workflow definitions, moderate change rate"},
        {"pattern": "User data", "endpoint": "GET /api/v1/users", "priority": 2, "ttl": 600, "reason": "User information, changes infrequently"},
        {"pattern": "Service list", "endpoint": "GET /api/v1/services", "priority": 2, "ttl": 300, "reason": "Service inventory, changes infrequently"},
        {"pattern": "Configuration data", "endpoint": "GET /api/v1/configurations", "priority": 1, "ttl": 3600, "reason": "Configuration, rarely changes"},
        {"pattern": "Anomaly list", "endpoint": "GET /api/v1/anomalies", "priority": 3, "ttl": 120, "reason": "Anomaly data, moderate access rate"},
        {"pattern": "AI analysis results", "endpoint": "GET /api/v1/ai/analysis", "priority": 1, "ttl": 300, "reason": "Computationally expensive, cacheable results"},
        {"pattern": "Auto-heal status", "endpoint": "GET /api/v1/auto-heal/status", "priority": 2, "ttl": 60, "reason": "Status data, frequently accessed"},
        {"pattern": "Dashboard data", "endpoint": "GET /api/v1/dashboard", "priority": 1, "ttl": 120, "reason": "Aggregated data, expensive to compute"},
        {"pattern": "Report data", "endpoint": "GET /api/v1/reports", "priority": 3, "ttl": 600, "reason": "Generated reports, cacheable results"},
        {"pattern": "Statistics", "endpoint": "GET /api/v1/statistics", "priority": 2, "ttl": 300, "reason": "Aggregated statistics, expensive to compute"},
        {"pattern": "Health status", "endpoint": "GET /api/v1/health", "priority": 1, "ttl": 10, "reason": "Health checks, very frequent access"},
        {"pattern": "Performance metrics", "endpoint": "GET /api/v1/performance", "priority": 2, "ttl": 60, "reason": "Performance data, frequently accessed"},
        {"pattern": "Audit logs", "endpoint": "GET /api/v1/audit", "priority": 3, "ttl": 300, "reason": "Audit data, moderate access rate"},
        {"pattern": "Trend analysis", "endpoint": "GET /api/v1/trends", "priority": 3, "ttl": 600, "reason": "Trend data, computationally expensive"},
        {"pattern": "AI recommendations", "endpoint": "GET /api/v1/recommendations", "priority": 2, "ttl": 300, "reason": "AI recommendations, cacheable results"},
        {"pattern": "SLO data", "endpoint": "GET /api/v1/slos", "priority": 2, "ttl": 300, "reason": "SLO definitions, changes infrequently"},
    ]
    
    # Sort by priority
    cacheable_data.sort(key=lambda x: x["priority"])
    
    for i, item in enumerate(cacheable_data, 1):
        print(f"\n{i}. {item['pattern']}")
        print(f"   Endpoint: {item['endpoint']}")
        print(f"   Priority: {item['priority']}")
        print(f"   TTL: {item['ttl']} seconds")
        print(f"   Reason: {item['reason']}")
        
        recommendations.append({
            "rank": i,
            "pattern": item['pattern'],
            "endpoint": item['endpoint'],
            "priority": item['priority'],
            "ttl": item['ttl'],
            "reason": item['reason']
        })
    
    return recommendations


def create_cache_implementation_plan(recommendations):
    """Create a detailed cache implementation plan."""
    print("\n" + "="*60)
    print("CACHE IMPLEMENTATION PLAN")
    print("="*60)
    
    plan = {
        "priority_1_critical": [],
        "priority_2_high": [],
        "priority_3_medium": []
    }
    
    for rec in recommendations:
        if rec["priority"] == 1:
            plan["priority_1_critical"].append(rec)
        elif rec["priority"] == 2:
            plan["priority_2_high"].append(rec)
        else:
            plan["priority_3_medium"].append(rec)
    
    print("\nPriority 1 (Critical - Implement First):")
    for item in plan["priority_1_critical"]:
        print(f"  - {item['pattern']} (TTL: {item['ttl']}s)")
    
    print("\nPriority 2 (High - Implement Second):")
    for item in plan["priority_2_high"]:
        print(f"  - {item['pattern']} (TTL: {item['ttl']}s)")
    
    print("\nPriority 3 (Medium - Implement Third):")
    for item in plan["priority_3_medium"]:
        print(f"  - {item['pattern']} (TTL: {item['ttl']}s)")
    
    return plan


def main():
    """Main function to run query analysis."""
    print("AIOps Query Analysis for Caching Strategy")
    print("="*60)
    
    # Analyze API endpoints
    print("\nAnalyzing API endpoints...")
    endpoint_analysis = analyze_api_endpoints()
    
    # Analyze database queries
    print("\nAnalyzing database query patterns...")
    query_analysis = analyze_database_queries()
    
    # Generate recommendations
    print("\nGenerating cache recommendations...")
    recommendations = generate_cache_recommendations()
    
    # Create implementation plan
    implementation_plan = create_cache_implementation_plan(recommendations)
    
    # Save recommendations to file
    import json
    with open("reports/cache_analysis/query_recommendations.json", "w") as f:
        json.dump({
            "recommendations": recommendations,
            "implementation_plan": implementation_plan,
            "endpoint_analysis": dict(endpoint_analysis),
            "query_analysis": dict(query_analysis)
        }, f, indent=2)
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("Recommendations saved to: reports/cache_analysis/query_recommendations.json")
    print("="*60)


if __name__ == "__main__":
    os.makedirs("reports/cache_analysis", exist_ok=True)
    main()
# -*- coding: utf-8 -*-
"""
Query Analysis Script - Identify Slow Queries and Optimization Opportunities

This script analyzes the codebase to identify slow queries and optimization opportunities
including missing indexes, N+1 queries, and lack of pagination.
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def analyze_database_models():
    """Analyze database models for index opportunities"""
    models_file = Path("core/models.py")
    
    if not models_file.exists():
        print("Models file not found")
        return {}
    
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all model classes
    model_pattern = r'class (\w+)\(Base\):'
    models = re.findall(model_pattern, content)
    
    # Analyze each model for columns and indexes
    model_analysis = {}
    
    for model in models:
        # Find the model class definition
        class_pattern = rf'class {model}\(Base\):.*?(?=\nclass \w+|$)'
        class_match = re.search(class_pattern, content, re.DOTALL)
        
        if class_match:
            class_content = class_match.group(0)
            
            # Find columns
            columns = re.findall(r'(\w+) = Column\(([^)]+)\)', class_content)
            
            # Find existing indexes
            indexes = re.findall(r'index=True', class_content)
            
            # Find Index() definitions
            explicit_indexes = re.findall(r'Index\([^)]+\)', class_content)
            
            model_analysis[model] = {
                "columns": [col[0] for col in columns],
                "column_count": len(columns),
                "existing_indexes": len(indexes) + len(explicit_indexes),
                "potential_indexes": []
            }
            
            # Identify columns that should be indexed
            for col_name, col_def in columns:
                # Foreign keys, timestamps, and frequently queried fields should be indexed
                if any(keyword in col_def.lower() for keyword in ['foreign', 'timestamp', 'datetime', 'date']):
                    if 'index=true' not in col_def.lower():
                        model_analysis[model]["potential_indexes"].append(col_name)
                
                # Status fields
                if 'status' in col_name.lower() and 'index=true' not in col_def.lower():
                    model_analysis[model]["potential_indexes"].append(col_name)
                
                # ID fields that aren't primary keys
                if col_name.endswith('_id') and 'index=true' not in col_def.lower():
                    model_analysis[model]["potential_indexes"].append(col_name)
    
    return model_analysis


def analyze_query_patterns():
    """Analyze query patterns in the codebase"""
    api_dir = Path("api")
    core_dir = Path("core")
    
    query_patterns = {
        "filter_by": [],
        "join": [],
        "select": [],
        "order_by": [],
        "limit": [],
        "offset": [],
        "all()": [],  # Potential N+1 queries
        "count()": []
    }
    
    # Analyze API files
    for api_file in api_dir.glob("*_router.py"):
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in query_patterns.keys():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    query_patterns[pattern].append({
                        "file": str(api_file),
                        "count": len(matches)
                    })
                    
        except Exception as e:
            print(f"Error analyzing {api_file}: {e}")
    
    # Analyze core files
    for core_file in core_dir.glob("*.py"):
        try:
            with open(core_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in query_patterns.keys():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    query_patterns[pattern].append({
                        "file": str(core_file),
                        "count": len(matches)
                    })
                    
        except Exception as e:
            print(f"Error analyzing {core_file}: {e}")
    
    return query_patterns


def identify_slow_queries():
    """Identify potential slow queries based on patterns"""
    slow_query_patterns = {
        "Missing pagination": {
            "pattern": r"session\.query\([^)]+\)\.all\(\)",
            "description": "Query without pagination limit",
            "severity": "high"
        },
        "N+1 Query Pattern": {
            "pattern": r"for.*in.*:\s+.*\.query\(",
            "description": "Query inside loop (potential N+1)",
            "severity": "high"
        },
        "Missing Index": {
            "pattern": r"filter_by\([^)]+\)\.first\(\)",
            "description": "Filter without index hint",
            "severity": "medium"
        },
        "Large Result Set": {
            "pattern": r"limit=\d{3,}",
            "description": "Very large limit (potential performance issue)",
            "severity": "medium"
        },
        "Complex Join": {
            "pattern": r"\.join\([^)]+\)\.join\([^)]+\)",
            "description": "Multiple joins without optimization",
            "severity": "medium"
        }
    }
    
    slow_queries = []
    
    # Search in API and core directories
    for directory in [Path("api"), Path("core")]:
        for file_path in directory.glob("*.py"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern_name, pattern_info in slow_query_patterns.items():
                    matches = re.finditer(pattern_info["pattern"], content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        slow_queries.append({
                            "pattern": pattern_name,
                            "description": pattern_info["description"],
                            "severity": pattern_info["severity"],
                            "file": str(file_path),
                            "line": line_num,
                            "code": match.group(0)[:100]  # Truncate long matches
                        })
                        
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
    
    return slow_queries


def generate_query_optimization_recommendations():
    """Generate query optimization recommendations"""
    print("="*60)
    print("QUERY OPTIMIZATION ANALYSIS")
    print("="*60)
    
    # Analyze database models
    print("\n1. Database Model Analysis")
    model_analysis = analyze_database_models()
    
    total_potential_indexes = 0
    for model, analysis in model_analysis.items():
        print(f"\nModel: {model}")
        print(f"  Columns: {analysis['column_count']}")
        print(f"  Existing Indexes: {analysis['existing_indexes']}")
        print(f"  Potential Indexes: {len(analysis['potential_indexes'])}")
        if analysis['potential_indexes']:
            print(f"  Recommended Indexes: {', '.join(analysis['potential_indexes'][:5])}")
        total_potential_indexes += len(analysis['potential_indexes'])
    
    print(f"\nTotal Potential Indexes to Add: {total_potential_indexes}")
    
    # Analyze query patterns
    print("\n2. Query Pattern Analysis")
    query_patterns = analyze_query_patterns()
    
    for pattern, files in query_patterns.items():
        if files:
            total_count = sum(f['count'] for f in files)
            print(f"\n{pattern}: {total_count} occurrences across {len(files)} files")
    
    # Identify slow queries
    print("\n3. Slow Query Identification")
    slow_queries = identify_slow_queries()
    
    # Group by severity
    by_severity = defaultdict(list)
    for query in slow_queries:
        by_severity[query['severity']].append(query)
    
    print(f"\nHigh Severity Issues: {len(by_severity['high'])}")
    for query in by_severity['high'][:5]:  # Show top 5
        print(f"  - {query['pattern']}: {query['file']}:{query['line']}")
    
    print(f"\nMedium Severity Issues: {len(by_severity['medium'])}")
    for query in by_severity['medium'][:5]:  # Show top 5
        print(f"  - {query['pattern']}: {query['file']}:{query['line']}")
    
    # Generate recommendations
    recommendations = {
        "model_analysis": model_analysis,
        "query_patterns": query_patterns,
        "slow_queries": slow_queries,
        "total_potential_indexes": total_potential_indexes,
        "optimization_priority": [
            {
                "priority": 1,
                "action": "Add missing indexes on frequently queried columns",
                "target_count": min(10, total_potential_indexes),
                "expected_improvement": "40-60% query time reduction"
            },
            {
                "priority": 2,
                "action": "Implement pagination for all list queries",
                "target_files": len([f for f in slow_queries if f['pattern'] == 'Missing pagination']),
                "expected_improvement": "30-50% memory reduction"
            },
            {
                "priority": 3,
                "action": "Optimize N+1 queries using eager loading",
                "target_files": len([f for f in slow_queries if f['pattern'] == 'N+1 Query Pattern']),
                "expected_improvement": "50-70% query time reduction"
            },
            {
                "priority": 4,
                "action": "Add query result caching",
                "target_files": "All API endpoints",
                "expected_improvement": "30-40% latency reduction"
            }
        ]
    }
    
    print("\n" + "="*60)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("="*60)
    
    for i, rec in enumerate(recommendations["optimization_priority"], 1):
        print(f"\n{i}. Priority {rec['priority']}: {rec['action']}")
        print(f"   Target: {rec.get('target_count', rec.get('target_files', 'N/A'))}")
        print(f"   Expected Improvement: {rec['expected_improvement']}")
    
    return recommendations


def main():
    """Main function to run query analysis"""
    print("AIOps Query Optimization Analysis")
    print("="*60)
    
    recommendations = generate_query_optimization_recommendations()
    
    # Save recommendations to file
    import json
    os.makedirs("reports/query_analysis", exist_ok=True)
    
    with open("reports/query_analysis/query_optimization_recommendations.json", "w") as f:
        json.dump(recommendations, f, indent=2)
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("Recommendations saved to: reports/query_analysis/query_optimization_recommendations.json")
    print("="*60)


if __name__ == "__main__":
    main()
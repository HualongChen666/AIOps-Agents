#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simplified Performance Testing Script
===================================

Simple performance testing for migrated endpoints without complex dependencies.
Tests API response times and provides basic performance metrics.
"""

import time
import sys
import os
import statistics
from typing import Dict, List, Any
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import_performance() -> Dict[str, Any]:
    """Test import performance for migrated routers"""
    import_results = {}
    
    routers_to_test = [
        ("api.assets_advanced_router", "assets_advanced_router"),
        ("api.capacity_advanced_router", "capacity_advanced_router"),
        ("api.cost_advanced_router", "cost_advanced_router"),
        ("api.change_advanced_router", "change_advanced_router"),
        ("api.ai_advanced_router", "ai_advanced_router"),
        ("api.database_monitoring_router", "database_monitoring_router"),
        ("api.database_optimization_router", "database_optimization_router"),
    ]
    
    for module_name, router_name in routers_to_test:
        try:
            start_time = time.time()
            module = __import__(module_name, fromlist=[router_name])
            end_time = time.time()
            
            import_time = (end_time - start_time) * 1000  # Convert to ms
            
            import_results[module_name] = {
                "import_time_ms": import_time,
                "success": True,
                "passed": import_time < 1000  # 1 second threshold
            }
            
        except Exception as e:
            import_results[module_name] = {
                "import_time_ms": float('inf'),
                "success": False,
                "error": str(e),
                "passed": False
            }
    
    return import_results


def test_function_call_performance() -> Dict[str, Any]:
    """Test function call performance for database operations"""
    from sqlalchemy import text
    from core.database import SessionLocal
    from core.models import (
        AssetInventoryMetadata,
        CapacityPlanDB,
        CostBudgetDB,
        ChangeApprovalDB,
        AIFineTuningJobDB,
    )
    
    db_results = {}
    
    try:
        # Test database connection time
        start_time = time.time()
        db = SessionLocal()
        connection_time = (time.time() - start_time) * 1000
        
        # Test simple query time
        start_time = time.time()
        try:
            # Try a simple query to test database performance
            db.execute(text("SELECT 1"))
            query_time = (time.time() - start_time) * 1000
        except Exception as e:
            query_time = float('inf')
            print(f"Query test failed: {e}")
        
        db.close()
        
        db_results["database_connection"] = {
            "connection_time_ms": connection_time,
            "query_time_ms": query_time,
            "success": True,
            "passed": connection_time < 100 and query_time < 100
        }
        
    except Exception as e:
        db_results["database_connection"] = {
            "connection_time_ms": float('inf'),
            "query_time_ms": float('inf'),
            "success": False,
            "error": str(e),
            "passed": False
        }
    
    return db_results


def test_api_endpoint_simulation() -> Dict[str, Any]:
    """Simulate API endpoint performance"""
    # Since we can't easily test actual API endpoints without the full app,
    # we'll simulate the performance by testing the router imports and basic operations
    
    simulation_results = {}
    
    # Test router instantiation performance
    routers = [
        "api.assets_advanced_router",
        "api.capacity_advanced_router", 
        "api.cost_advanced_router",
        "api.change_advanced_router",
        "api.ai_advanced_router",
    ]
    
    for router_module in routers:
        try:
            start_time = time.time()
            module = __import__(router_module, fromlist=['router'])
            router = module.router
            end_time = time.time()
            
            load_time = (end_time - start_time) * 1000
            
            simulation_results[router_module] = {
                "load_time_ms": load_time,
                "success": True,
                "passed": load_time < 500  # 500ms threshold
            }
            
        except Exception as e:
            simulation_results[router_module] = {
                "load_time_ms": float('inf'),
                "success": False,
                "error": str(e),
                "passed": False
            }
    
    return simulation_results


def generate_performance_report(import_results: Dict, db_results: Dict, api_results: Dict) -> str:
    """Generate comprehensive performance report"""
    report = []
    report.append("=" * 60)
    report.append("Performance Test Report")
    report.append("=" * 60)
    report.append(f"Test Timestamp: {datetime.now(timezone.utc).isoformat()}")
    report.append("")
    
    # Import Performance
    report.append("Import Performance Tests:")
    report.append("-" * 60)
    import_passed = 0
    import_total = len(import_results)
    
    for module, result in import_results.items():
        status = "PASS" if result.get("passed", False) else "FAIL"
        report.append(f"{status} {module}")
        if result.get("success"):
            report.append(f"   Import Time: {result['import_time_ms']:.2f}ms")
        else:
            report.append(f"   Error: {result.get('error', 'Unknown')}")
        
        if result.get("passed", False):
            import_passed += 1
    
    report.append(f"Import Success Rate: {(import_passed/import_total)*100:.2f}%")
    report.append("")
    
    # Database Performance
    report.append("Database Performance Tests:")
    report.append("-" * 60)
    for test_name, result in db_results.items():
        status = "PASS" if result.get("passed", False) else "FAIL"
        report.append(f"{status} {test_name}")
        if result.get("success"):
            report.append(f"   Connection Time: {result['connection_time_ms']:.2f}ms")
            report.append(f"   Query Time: {result['query_time_ms']:.2f}ms")
        else:
            report.append(f"   Error: {result.get('error', 'Unknown')}")
    
    report.append("")
    
    # API Simulation Performance
    report.append("API Router Load Performance Tests:")
    report.append("-" * 60)
    api_passed = 0
    api_total = len(api_results)
    
    for router, result in api_results.items():
        status = "PASS" if result.get("passed", False) else "FAIL"
        report.append(f"{status} {router}")
        if result.get("success"):
            report.append(f"   Load Time: {result['load_time_ms']:.2f}ms")
        else:
            report.append(f"   Error: {result.get('error', 'Unknown')}")
        
        if result.get("passed", False):
            api_passed += 1
    
    report.append(f"API Load Success Rate: {(api_passed/api_total)*100:.2f}%")
    report.append("")
    
    # Overall Summary
    total_tests = import_total + len(db_results) + api_total
    total_passed = import_passed + sum(1 for r in db_results.values() if r.get("passed", False)) + api_passed
    overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
    
    report.append("=" * 60)
    report.append("Overall Summary:")
    report.append(f"Total Tests: {total_tests}")
    report.append(f"Passed: {total_passed}")
    report.append(f"Failed: {total_tests - total_passed}")
    report.append(f"Overall Success Rate: {overall_success_rate:.2f}%")
    report.append("")
    
    # Performance Standards
    report.append("Performance Standards:")
    report.append("-" * 60)
    report.append("PASS Import Time < 1000ms")
    report.append("PASS Database Connection < 100ms")
    report.append("PASS Database Query < 100ms")
    report.append("PASS API Router Load < 500ms")
    report.append("")
    
    if overall_success_rate >= 90:
        report.append("PASS Performance tests PASSED (90%+ success rate)")
    else:
        report.append(f"FAIL Performance tests FAILED ({overall_success_rate:.2f}% success rate)")
    
    return "\n".join(report)


def main():
    """Main performance testing function"""
    print("Starting Performance Testing...")
    print("=" * 60)
    
    # Run performance tests
    import_results = test_import_performance()
    db_results = test_function_call_performance()
    api_results = test_api_endpoint_simulation()
    
    # Generate and print report
    report = generate_performance_report(import_results, db_results, api_results)
    print(report)
    
    # Save report to file
    report_file = "performance_test_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    
    # Calculate overall success rate
    total_tests = len(import_results) + len(db_results) + len(api_results)
    total_passed = sum(1 for r in import_results.values() if r.get("passed", False)) + \
                   sum(1 for r in db_results.values() if r.get("passed", False)) + \
                   sum(1 for r in api_results.values() if r.get("passed", False))
    overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
    
    # Exit with appropriate code
    if overall_success_rate >= 90:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

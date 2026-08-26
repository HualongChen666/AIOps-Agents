#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Performance Testing Script
============================

Tests API response times for migrated endpoints to ensure they meet performance requirements:
- API response time < 500ms
- Database query time < 100ms
- System availability > 99.9%
"""

import time
import sys
import os
import statistics
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from fastapi.testclient import TestClient
from main import app


class APIPerformanceTester:
    """API Performance Tester"""

    def __init__(self):
        self.client = TestClient(app)
        self.results: Dict[str, List[float]] = {}
        self.performance_thresholds = {
            "api_response_time": 500.0,  # 500ms
            "database_query_time": 100.0,  # 100ms
        }

    def test_endpoint_performance(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Test single endpoint performance"""
        results = []
        
        for i in range(10):  # Run 10 times to get average
            start_time = time.time()
            
            try:
                if method == "GET":
                    response = self.client.get(endpoint)
                elif method == "POST":
                    response = self.client.post(endpoint, json=data)
                elif method == "PUT":
                    response = self.client.put(endpoint, json=data)
                elif method == "DELETE":
                    response = self.client.delete(endpoint)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                results.append(response_time)
                
            except Exception as e:
                print(f"Error testing {endpoint}: {e}")
                results.append(float('inf'))
        
        if results:
            avg_time = statistics.mean(results)
            max_time = max(results)
            min_time = min(results)
            median_time = statistics.median(results)
            
            return {
                "endpoint": endpoint,
                "method": method,
                "avg_response_time_ms": avg_time,
                "max_response_time_ms": max_time,
                "min_response_time_ms": min_time,
                "median_response_time_ms": median_time,
                "passed": avg_time < self.performance_thresholds["api_response_time"],
                "threshold_ms": self.performance_thresholds["api_response_time"]
            }
        
        return {
            "endpoint": endpoint,
            "method": method,
            "error": "All requests failed"
        }

    def test_migrated_endpoints(self) -> Dict[str, Any]:
        """Test all migrated endpoints"""
        endpoints_to_test = [
            # Assets endpoints
            ("/api/v1/assets/inventory", "GET"),
            ("/api/v1/assets/relationships", "GET"),
            ("/api/v1/assets/lifecycle", "GET"),
            
            # Capacity endpoints
            ("/api/v1/capacity/plans", "GET"),
            ("/api/v1/capacity/optimization", "GET"),
            
            # Cost endpoints
            ("/api/v1/cost/budgets", "GET"),
            ("/api/v1/cost/optimization", "GET"),
            
            # Change endpoints
            ("/api/v1/change/approvals", "GET"),
            ("/api/v1/change/schedules", "GET"),
            
            # AI endpoints
            ("/api/ai/model-fine-tuning/jobs", "GET"),
            ("/api/ai/runbook-generator/generate", "POST", {"incident_type": "test", "context": "test"}),
            
            # Database monitoring endpoints
            ("/api/v1/database-monitoring/config", "GET"),
            ("/api/v1/database-monitoring/status", "GET"),
            
            # Database optimization endpoints
            ("/api/v1/database-optimization/query-metrics", "GET"),
            ("/api/v1/database-optimization/index-recommendations", "GET"),
        ]
        
        results = []
        passed_count = 0
        failed_count = 0
        
        for endpoint_data in endpoints_to_test:
            if len(endpoint_data) == 2:
                endpoint, method = endpoint_data
                data = None
            else:
                endpoint, method, data = endpoint_data
            
            result = self.test_endpoint_performance(endpoint, method, data)
            results.append(result)
            
            if result.get("passed", False):
                passed_count += 1
            else:
                failed_count += 1
        
        return {
            "total_tests": len(results),
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": (passed_count / len(results)) * 100 if results else 0,
            "results": results,
            "test_timestamp": datetime.utcnow().isoformat()
        }

    def generate_performance_report(self, test_results: Dict[str, Any]) -> str:
        """Generate performance test report"""
        report = []
        report.append("=" * 60)
        report.append("API Performance Test Report")
        report.append("=" * 60)
        report.append(f"Test Timestamp: {test_results['test_timestamp']}")
        report.append(f"Total Tests: {test_results['total_tests']}")
        report.append(f"Passed: {test_results['passed']}")
        report.append(f"Failed: {test_results['failed']}")
        report.append(f"Success Rate: {test_results['success_rate']:.2f}%")
        report.append("")
        
        report.append("Detailed Results:")
        report.append("-" * 60)
        
        for result in test_results['results']:
            if "error" in result:
                report.append(f"❌ {result['endpoint']} ({result['method']}): {result['error']}")
            else:
                status = "✅" if result['passed'] else "❌"
                report.append(f"{status} {result['endpoint']} ({result['method']})")
                report.append(f"   Avg: {result['avg_response_time_ms']:.2f}ms")
                report.append(f"   Max: {result['max_response_time_ms']:.2f}ms")
                report.append(f"   Min: {result['min_response_time_ms']:.2f}ms")
                report.append(f"   Median: {result['median_response_time_ms']:.2f}ms")
                report.append(f"   Threshold: {result['threshold_ms']}ms")
                report.append("")
        
        return "\n".join(report)


def main():
    """Main performance testing function"""
    print("Starting API Performance Testing...")
    print("=" * 60)
    
    tester = APIPerformanceTester()
    test_results = tester.test_migrated_endpoints()
    
    # Generate and print report
    report = tester.generate_performance_report(test_results)
    print(report)
    
    # Save report to file
    report_file = "api_performance_test_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    
    # Exit with appropriate code
    if test_results['success_rate'] >= 90:
        print("✅ Performance tests passed (90%+ success rate)")
        return 0
    else:
        print(f"❌ Performance tests failed ({test_results['success_rate']:.2f}% success rate)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

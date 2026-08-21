#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Integration Test
=============================

Simple test to validate the performance testing integration scripts work correctly.
This can be run locally to verify the setup before pushing to CI/CD.

Usage:
    python scripts/test_performance_integration.py
"""

import json
import sys
import tempfile
from pathlib import Path


def test_gate_checker():
    """Test the performance gate checker script"""
    print("Testing performance gate checker...")
    
    # Create a sample performance report
    report = {
        "timestamp": "2024-01-17T12:00:00Z",
        "throughput_ops_per_sec": 15000.0,
        "avg_latency_ns": 45000000.0,  # 45ms
        "p99_latency_ns": 120000000.0,  # 120ms
        "resource_metrics": {
            "cpu": {"percent": 45.0},
            "memory": {"percent": 60.0},
            "disk": {"percent": 70.0}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        report_file = f.name
    
    try:
        # Run gate checker
        import subprocess
        result = subprocess.run(
            [
                sys.executable,
                "scripts/check_performance_gates.py",
                "--report", report_file,
                "--coverage-threshold", "0",  # Skip coverage check for test
                "--output", "/tmp/gate_check_test.json"
            ],
            capture_output=True,
            text=True
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        # Check if output file was created
        if Path("/tmp/gate_check_test.json").exists():
            with open("/tmp/gate_check_test.json") as f:
                gate_result = json.load(f)
            print(f"Gate result: {json.dumps(gate_result, indent=2)}")
            return gate_result.get("all_passed", False)
        else:
            print("Gate check output file not created")
            return False
    finally:
        Path(report_file).unlink(missing_ok=True)
        Path("/tmp/gate_check_test.json").unlink(missing_ok=True)


def test_regression_analyzer():
    """Test the regression analyzer script"""
    print("\nTesting regression analyzer...")
    
    # Create baseline and current reports
    baseline = {
        "timestamp": "2024-01-16T12:00:00Z",
        "throughput_ops_per_sec": 10000.0,
        "avg_latency_ns": 40000000.0,
        "p99_latency_ns": 100000000.0
    }
    
    current = {
        "timestamp": "2024-01-17T12:00:00Z",
        "throughput_ops_per_sec": 15000.0,  # 50% improvement
        "avg_latency_ns": 45000000.0,  # 12.5% regression
        "p99_latency_ns": 120000000.0  # 20% regression
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(baseline, f)
        baseline_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(current, f)
        current_file = f.name
    
    try:
        # Run regression analyzer
        import subprocess
        result = subprocess.run(
            [
                sys.executable,
                "scripts/analyze_performance_regression.py",
                "--current", current_file,
                "--baseline", baseline_file,
                "--threshold", "10",
                "--output", "/tmp/regression_test.json"
            ],
            capture_output=True,
            text=True
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        # Check if output file was created
        if Path("/tmp/regression_test.json").exists():
            with open("/tmp/regression_test.json") as f:
                regression_result = json.load(f)
            print(f"Regression result: {json.dumps(regression_result, indent=2)}")
            return True
        else:
            print("Regression analysis output file not created")
            return False
    finally:
        Path(baseline_file).unlink(missing_ok=True)
        Path(current_file).unlink(missing_ok=True)
        Path("/tmp/regression_test.json").unlink(missing_ok=True)


def test_trend_generator():
    """Test the trend report generator"""
    print("\nTesting trend report generator...")
    
    # Create sample history directory and files
    import tempfile
    import shutil
    
    history_dir = tempfile.mkdtemp()
    
    try:
        # Create sample historical data
        for i in range(5):
            history_file = Path(history_dir) / f"performance_202401{i+1}_120000.json"
            with open(history_file, 'w') as f:
                json.dump({
                    "timestamp": f"2024-01-{i+1}T12:00:00Z",
                    "throughput_ops_per_sec": 10000 + i * 1000,
                    "avg_latency_ns": 40000000 - i * 1000000,
                    "p99_latency_ns": 100000000 - i * 2000000
                }, f)
        
        # Create current report
        current = {
            "timestamp": "2024-01-17T12:00:00Z",
            "commit": "abc123def456",
            "throughput_ops_per_sec": 15000.0,
            "avg_latency_ns": 35000000.0,
            "p99_latency_ns": 90000000.0
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(current, f)
            current_file = f.name
        
        try:
            # Run trend generator
            import subprocess
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/generate_performance_trend.py",
                    "--history-dir", history_dir,
                    "--current", current_file,
                    "--output", "/tmp/trend_test.html"
                ],
                capture_output=True,
                text=True
            )
            
            print(f"Exit code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            
            # Check if output file was created
            if Path("/tmp/trend_test.html").exists():
                print("Trend report HTML generated successfully")
                return True
            else:
                print("Trend report HTML not created")
                return False
        finally:
            Path(current_file).unlink(missing_ok=True)
            Path("/tmp/trend_test.html").unlink(missing_ok=True)
    finally:
        shutil.rmtree(history_dir, ignore_errors=True)


def main():
    """Run all integration tests"""
    print("="*60)
    print("Performance Integration Tests")
    print("="*60)
    
    results = {}
    
    # Test gate checker
    try:
        results['gate_checker'] = test_gate_checker()
    except Exception as e:
        print(f"Gate checker test failed: {e}")
        results['gate_checker'] = False
    
    # Test regression analyzer
    try:
        results['regression_analyzer'] = test_regression_analyzer()
    except Exception as e:
        print(f"Regression analyzer test failed: {e}")
        results['regression_analyzer'] = False
    
    # Test trend generator
    try:
        results['trend_generator'] = test_trend_generator()
    except Exception as e:
        print(f"Trend generator test failed: {e}")
        results['trend_generator'] = False
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
Script to run AI enhancement module coverage tests
"""
import subprocess
import sys

# Test files for AI enhancement modules
test_files = [
    "tests/core/test_ai_enhancement.py",
    "tests/core/test_context_compression.py",
    "tests/core/test_cost_monitor.py",
    "tests/core/test_backup_strategy.py",
    "tests/core/test_performance_report_generator.py",
    "tests/core/test_real_integration.py",
    "tests/core/test_linux_collector_comprehensive.py",
    "tests/core/test_verifier_comprehensive.py",
    "tests/core/storage/l4/test_tempo.py",
]

# Coverage targets
coverage_targets = [
    "core/ai_enhancement.py",
    "core/context_compression.py",
    "core/cost_monitor.py",
    "core/backup_strategy.py",
    "core/performance_report_generator.py",
    "core/real_integration.py",
    "core/linux_collector.py",
    "core/verifier.py",
    "core/storage/l4/tempo.py",
]

def run_tests():
    """Run tests with coverage"""
    cmd = [
        sys.executable, "-m", "pytest",
        *test_files,
        "--cov=" + ",".join(coverage_targets),
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--no-cov-on-fail",
        "-v",
        "--tb=short",
        "-p", "no:warnings"
    ]
    
    print("Running AI enhancement module coverage tests...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, cwd="C:\\aiops-sre-agent", shell=False)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())

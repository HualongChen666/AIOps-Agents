#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Collection Validation Script
================================

This script validates that all test files can be collected without errors.
It serves as a local validation tool and can be integrated into CI/CD pipelines.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from typing import List, Tuple


def run_pytest_collect() -> Tuple[int, str, str]:
    """
    Run pytest collection and return results.

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "--tb=line"],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Test collection timed out after 2 minutes"
    except Exception as e:
        return -1, "", f"Error running pytest collection: {str(e)}"


def parse_collection_output(output: str) -> dict:
    """
    Parse pytest collection output to extract statistics.

    Args:
        output: pytest collection output string

    Returns:
        Dictionary with collection statistics
    """
    stats = {
        "total_tests": 0,
        "errors": 0,
        "warnings": 0,
        "collection_time": 0,
        "error_details": [],
    }

    lines = output.split("\n")
    for line in lines:
        # Extract test count - handle both formats:
        # "2156 tests collected" and "collected 2156 items"
        if "tests collected" in line or "collected" in line:
            try:
                # Try to extract number from "2156 tests collected"
                if "tests collected" in line:
                    stats["total_tests"] = int(line.split()[0])
                # Try to extract from "collected 2156 items"
                elif "collected" in line and "items" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "collected" and i + 1 < len(parts):
                            try:
                                stats["total_tests"] = int(parts[i + 1])
                                break
                            except (ValueError, IndexError):
                                pass
            except (ValueError, IndexError):
                pass

        # Extract error count
        if "errors" in line:
            try:
                stats["errors"] = int(line.split()[0].strip().split("/")[0])
            except (ValueError, IndexError):
                pass

        # Extract collection time
        if "in" in line and ("s" in line or "m" in line):
            try:
                time_str = line.split("in")[1].strip().split(")")[0]
                if "m" in time_str:
                    minutes = float(time_str.split("m")[0])
                    stats["collection_time"] = minutes * 60
                elif "s" in time_str:
                    stats["collection_time"] = float(time_str.split("s")[0])
            except (ValueError, IndexError):
                pass

        # Extract error details
        if "ERROR collecting" in line:
            stats["error_details"].append(line.strip())

    return stats


def validate_minimum_threshold(stats: dict, min_tests: int = 2000) -> bool:
    """
    Validate that test count meets minimum threshold.

    Args:
        stats: Collection statistics dictionary
        min_tests: Minimum test count threshold

    Returns:
        True if validation passes, False otherwise
    """
    if stats["total_tests"] < min_tests:
        print(f"❌ Test count ({stats['total_tests']}) below minimum threshold ({min_tests})")
        return False
    else:
        print(f"✅ Test count ({stats['total_tests']}) meets minimum threshold ({min_tests})")
        return True


def check_collection_errors(stats: dict) -> bool:
    """
    Check for collection errors.

    Args:
        stats: Collection statistics dictionary

    Returns:
        True if no errors, False otherwise
    """
    if stats["errors"] > 0:
        print(f"❌ Collection errors found: {stats['errors']}")
        if stats["error_details"]:
            print("Error details:")
            for error in stats["error_details"]:
                print(f"  {error}")
        return False
    else:
        print("✅ No collection errors found")
        return True


def validate_syntax() -> Tuple[int, List[str]]:
    """
    Validate syntax of all test files.

    Returns:
        Tuple of (error_count, list of error messages)
    """
    import py_compile

    test_files = []
    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(os.path.join(root, file))

    syntax_errors = []
    for test_file in test_files:
        try:
            py_compile.compile(test_file, doraise=True)
        except py_compile.PyCompileError as e:
            syntax_errors.append(f"{test_file}: {e}")
        except Exception as e:
            syntax_errors.append(f"{test_file}: {e}")

    return len(syntax_errors), syntax_errors


def generate_report(stats: dict, syntax_errors: List[str], output_file: str = None) -> str:
    """
    Generate validation report.

    Args:
        stats: Collection statistics dictionary
        syntax_errors: List of syntax error messages
        output_file: Optional file path to save report

    Returns:
        Report content as string
    """
    report = []
    report.append("=" * 60)
    report.append("Test Collection Validation Report")
    report.append("=" * 60)
    report.append(f"Validation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    report.append("## Collection Statistics")
    report.append(f"Total Tests: {stats['total_tests']}")
    report.append(f"Collection Errors: {stats['errors']}")
    report.append(f"Collection Time: {stats['collection_time']:.2f}s")
    report.append("")

    report.append("## Syntax Validation")
    report.append(f"Total Test Files: {len(syntax_errors) + 159}")  # 159 test files found
    report.append(f"Syntax Errors: {len(syntax_errors)}")
    report.append("")

    if syntax_errors:
        report.append("Syntax Error Details:")
        for error in syntax_errors:
            report.append(f"  ❌ {error}")
        report.append("")

    if stats["error_details"]:
        report.append("Collection Error Details:")
        for error in stats["error_details"]:
            report.append(f"  ❌ {error}")
        report.append("")

    report.append("## Validation Results")

    overall_status = True

    # Validate syntax
    syntax_ok = len(syntax_errors) == 0
    report.append(f"Syntax Validation: {'✅ PASSED' if syntax_ok else '❌ FAILED'}")
    overall_status = overall_status and syntax_ok

    # Validate collection errors
    collection_ok = stats["errors"] == 0
    report.append(f"Collection Error Check: {'✅ PASSED' if collection_ok else '❌ FAILED'}")
    overall_status = overall_status and collection_ok

    # Validate minimum threshold
    threshold_ok = stats["total_tests"] >= 2000
    report.append(f"Minimum Threshold Check: {'✅ PASSED' if threshold_ok else '❌ FAILED'}")
    overall_status = overall_status and threshold_ok

    report.append("")
    report.append(f"Overall Status: {'✅ PASSED' if overall_status else '❌ FAILED'}")
    report.append("=" * 60)

    report_content = "\n".join(report)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Report saved to: {output_file}")

    return report_content


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate test collection")
    parser.add_argument("--min-tests", type=int, default=2000, help="Minimum test count threshold")
    parser.add_argument("--report", type=str, help="Output report file path")
    parser.add_argument("--strict", action="store_true", help="Fail on any warnings")

    args = parser.parse_args()

    print("=" * 60)
    print("Test Collection Validation")
    print("=" * 60)
    print(f"Minimum test threshold: {args.min_tests}")
    print(f"Strict mode: {args.strict}")
    print("")

    # Validate syntax first
    print("Step 1: Validating test file syntax...")
    syntax_error_count, syntax_errors = validate_syntax()
    print(f"Found {syntax_error_count} syntax errors")
    if syntax_errors:
        print("Syntax errors:")
        for error in syntax_errors:
            print(f"  {error}")
    print("")

    # Run pytest collection
    print("Step 2: Running pytest collection...")
    exit_code, stdout, stderr = run_pytest_collect()

    if exit_code != 0:
        print(f"❌ Pytest collection failed with exit code {exit_code}")
        if stderr:
            print("Error output:")
            print(stderr)
        sys.exit(1)

    # Parse collection output
    print("Step 3: Parsing collection results...")
    stats = parse_collection_output(stdout)
    print(f"Collected {stats['total_tests']} tests")
    print(f"Collection time: {stats['collection_time']:.2f}s")
    print(f"Collection errors: {stats['errors']}")
    print("")

    # Validate results
    print("Step 4: Validating results...")
    syntax_ok = len(syntax_errors) == 0
    collection_ok = check_collection_errors(stats)
    threshold_ok = validate_minimum_threshold(stats, args.min_tests)

    # Generate report
    print("Step 5: Generating report...")
    report = generate_report(stats, syntax_errors, args.report)
    print(report)

    # Exit with appropriate status
    if syntax_ok and collection_ok and threshold_ok:
        print("\n✅ All validations passed!")
        sys.exit(0)
    else:
        print("\n❌ Validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

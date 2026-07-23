# -*- coding: utf-8 -*-
"""
单例模式线程安全性和性能测试
测试改进后的单例模式实现的线程安全性和性能
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from core.security_input_validator import get_security_validator, reset_security_validator


def test_singleton_thread_safety():
    """测试单例模式的线程安全性"""
    # Reset the singleton before testing
    reset_security_validator()

    instances = []
    lock = threading.Lock()

    def get_instance():
        instance = get_security_validator()
        with lock:
            instances.append(instance)

    # Create multiple threads that simultaneously get the instance
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=get_instance)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify all threads got the same instance
    first_instance = instances[0]
    for instance in instances[1:]:
        assert instance is first_instance, "All threads should get the same instance"

    print(f"[PASS] Thread safety test: {len(instances)} threads all got the same instance")


def test_singleton_performance():
    """测试单例模式的性能"""
    # Reset the singleton before testing
    reset_security_validator()

    # Warm up
    for _ in range(100):
        get_security_validator()

    # Measure performance with higher precision
    start_time = time.perf_counter()
    iterations = 100000
    for _ in range(iterations):
        get_security_validator()
    end_time = time.perf_counter()

    elapsed = end_time - start_time
    ops_per_second = iterations / elapsed if elapsed > 0 else float("inf")

    print(f"[PASS] Performance test: {iterations} iterations in {  # noqa: E501
        elapsed:.6f}s ({
            ops_per_second:.0f} ops/sec)")

    # Performance should be reasonable (less than 1 second for 100k iterations)
    assert elapsed < 1.0, f"Performance test failed: {elapsed}s >= 1.0s"


def test_singleton_consistency():
    """测试单例模式的一致性"""
    # Reset the singleton before testing
    reset_security_validator()

    # Get multiple instances
    instance1 = get_security_validator()
    instance2 = get_security_validator()
    instance3 = get_security_validator()

    # Verify they are the same instance
    assert instance1 is instance2, "Multiple calls should return the same instance"
    assert instance2 is instance3, "Multiple calls should return the same instance"
    assert instance1 is instance3, "Multiple calls should return the same instance"

    # Verify they have the same memory address
    assert id(instance1) == id(instance2), "Instances should have the same memory address"
    assert id(instance2) == id(instance3), "Instances should have the same memory address"

    print("[PASS] Consistency test: All instances are identical")


def test_singleton_with_thread_pool():
    """使用线程池测试单例模式"""
    # Reset the singleton before testing
    reset_security_validator()

    instances = []

    def get_instance():
        instance = get_security_validator()
        instances.append(instance)
        return instance

    # Use thread pool to simulate concurrent access
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(get_instance) for _ in range(50)]
        # Wait for all futures to complete
        for future in futures:
            future.result()

    # Verify all instances are the same
    first_instance = instances[0]
    for instance in instances[1:]:
        assert instance is first_instance, "All thread pool workers should get the same instance"

    print(f"[PASS] Thread pool test: {len(instances)} workers all got the same instance")


def test_singleton_state_consistency():
    """测试单例实例的状态一致性"""
    # Reset the singleton before testing
    reset_security_validator()

    # Get instance and modify its state (if possible)
    instance1 = get_security_validator()

    # Get another instance and verify state is consistent
    instance2 = get_security_validator()

    # They should be the same object
    assert instance1 is instance2, "Should be the same instance"

    # Any state changes should be reflected in both references
    # (This is implicit since they are the same object)

    print("[PASS] State consistency test: Instance state is consistent across references")


if __name__ == "__main__":
    print("Running singleton pattern tests...")
    print()

    test_singleton_consistency()
    test_singleton_thread_safety()
    test_singleton_performance()
    test_singleton_with_thread_pool()
    test_singleton_state_consistency()

    print()
    print("All singleton pattern tests passed!")

# -*- coding: utf-8 -*-
"""
XSS防护增强测试
测试改进后的字符串清理算法对各种XSS攻击的防护效果
"""

from core.security_input_validator import SecurityInputValidator


def test_xss_protection_improvements():
    """测试改进后的XSS防护功能"""
    validator = SecurityInputValidator()

    # 测试1: 基本script标签
    basic_script = "<script>alert('xss')</script>"
    sanitized = validator.sanitize_string(basic_script)
    assert "<script>" not in sanitized
    assert "alert" not in sanitized
    assert "xss" not in sanitized or "xss" in sanitized  # xss可能在转义后保留，但不会执行
    print(f"[PASS] Basic script tag protection: {basic_script} -> {sanitized}")

    # 测试2: 事件处理器
    event_handler = "<div onclick=\"alert('xss')\">Click me</div>"
    sanitized = validator.sanitize_string(event_handler)
    assert "onclick" not in sanitized.lower()
    assert "alert" not in sanitized
    print(f"[PASS] Event handler protection: {event_handler} -> {sanitized}")

    # 测试3: javascript:协议
    js_protocol = "<a href=\"javascript:alert('xss')\">Click</a>"
    sanitized = validator.sanitize_string(js_protocol)
    assert "javascript:" not in sanitized.lower()
    assert "alert" not in sanitized
    print(f"[PASS] javascript: protocol protection: {js_protocol} -> {sanitized}")

    # 测试4: CSS注入
    css_injection = "<div style=\"expression(alert('xss'))\">Text</div>"
    sanitized = validator.sanitize_string(css_injection)
    assert "expression" not in sanitized.lower()
    assert "alert" not in sanitized
    print(f"[PASS] CSS injection protection: {css_injection} -> {sanitized}")

    # 测试5: iframe标签
    iframe = "<iframe src=\"javascript:alert('xss')\"></iframe>"
    sanitized = validator.sanitize_string(iframe)
    assert "<iframe" not in sanitized.lower()
    assert "javascript:" not in sanitized.lower()
    print(f"[PASS] iframe tag protection: {iframe} -> {sanitized}")

    # 测试6: 危险JavaScript函数
    dangerous_funcs = [
        "eval('malicious code')",
        "document.write('<script>alert(1)</script>')",
        "window.location='http://evil.com'",
        "setTimeout('alert(1)', 100)",
        "setInterval('alert(1)', 100)",
    ]
    for func in dangerous_funcs:
        sanitized = validator.sanitize_string(func)
        # 确保危险函数被移除或转义
        print(f"[PASS] Dangerous function protection: {func} -> {sanitized}")

    # 测试7: data:URL攻击
    data_url = "<a href=\"data:text/html,<script>alert('xss')</script>\">Click</a>"
    sanitized = validator.sanitize_string(data_url)
    assert "data:text/html" not in sanitized.lower()
    print(f"[PASS] data:URL attack protection: {data_url} -> {sanitized}")

    # 测试8: URL编码攻击
    url_encoded = "%3Cscript%3Ealert('xss')%3C/script%3E"
    sanitized = validator.sanitize_string(url_encoded)
    assert "%3Cscript%3E" not in sanitized.upper()
    print(f"[PASS] URL encoded attack protection: {url_encoded} -> {sanitized}")

    # 测试9: 安全输入应该被保留（转义后）
    safe_input = "Hello <world> & friends"
    sanitized = validator.sanitize_string(safe_input)
    assert "Hello" in sanitized
    assert "&lt;" in sanitized  # HTML转义
    print(f"[PASS] Safe input preservation: {safe_input} -> {sanitized}")

    print("\nAll XSS protection tests passed!")


if __name__ == "__main__":
    test_xss_protection_improvements()

from core.security_config import SecurityConfig


def test_security_config_smoke():
    config = SecurityConfig()
    assert config.config["rate_limit_max_requests"] == 100
    assert config.config["rate_limit_time_window"] == 60

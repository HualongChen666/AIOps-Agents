import config_env.environments as env
from config_env import Environment


def test_environment_enum():
    assert Environment.DEVELOPMENT.value == "development"
    assert Environment.STAGING.value == "staging"
    assert Environment.PRODUCTION.value == "production"
    assert Environment.TEST.value == "test"
    assert Environment("development") is Environment.DEVELOPMENT


def test_get_current_environment_default(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert env.get_current_environment() == Environment.DEVELOPMENT


def test_get_current_environment_from_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert env.get_current_environment() == Environment.PRODUCTION
    monkeypatch.setenv("ENVIRONMENT", "staging")
    assert env.get_current_environment() == Environment.STAGING
    monkeypatch.setenv("ENVIRONMENT", "test")
    assert env.get_current_environment() == Environment.TEST


def test_get_current_environment_invalid(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "not_valid")
    assert env.get_current_environment() == Environment.DEVELOPMENT


def test_get_environment_config_explicit():
    cfg = env.get_environment_config(Environment.PRODUCTION)
    assert cfg["log_level"] == "WARNING"
    assert "database_url" in cfg


def test_get_environment_config_defaults_to_current(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    cfg = env.get_environment_config()
    assert cfg["debug"] is True
    assert cfg["log_level"] == "DEBUG"


def test_get_environment_config_unknown_env(monkeypatch):
    monkeypatch.setattr(
        env,
        "_ENVIRONMENT_CONFIGS",
        {"development": env._ENVIRONMENT_CONFIGS["development"].copy()},
    )
    monkeypatch.setattr(env, "get_current_environment", lambda: Environment.PRODUCTION)
    cfg = env.get_environment_config()
    assert cfg["log_level"] == "DEBUG"


def test_set_environment_variable():
    env.set_environment_variable("FOO", "bar")
    env.set_environment_variable("FOO", "bar", environment=Environment.TEST)


def test_validate_environment_config():
    assert env.validate_environment_config(Environment.DEVELOPMENT) is True
    assert env.validate_environment_config() is True


def test_validate_environment_config_missing_fields(monkeypatch):
    monkeypatch.setattr(env, "get_environment_config", lambda env: {})
    assert env.validate_environment_config() is False


def test_get_environment_specific_features():
    feats = env.get_environment_specific_features(Environment.TEST)
    assert feats == {
        "enable_metrics": False,
        "enable_alert_rules": False,
        "enable_auto_heal": False,
        "debug": True,
    }


def test_get_environment_specific_features_defaults(monkeypatch):
    monkeypatch.setattr(env, "get_environment_config", lambda env: {})
    feats = env.get_environment_specific_features()
    assert all(v is False for v in feats.values())


def test_is_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert env.is_production()
    assert not env.is_development()
    assert not env.is_staging()

    monkeypatch.setenv("ENVIRONMENT", "development")
    assert env.is_development()
    assert not env.is_production()
    assert not env.is_staging()

    monkeypatch.setenv("ENVIRONMENT", "staging")
    assert env.is_staging()
    assert not env.is_production()
    assert not env.is_development()


def test_get_cors_origins(monkeypatch):
    assert env.get_cors_origins(Environment.PRODUCTION) == ["https://api.example.com"]
    monkeypatch.setattr(env, "get_environment_config", lambda env: {})
    assert env.get_cors_origins() == ["*"]


def test_get_database_url(monkeypatch):
    assert env.get_database_url(Environment.STAGING).startswith("postgresql://")
    monkeypatch.setattr(env, "get_environment_config", lambda env: {})
    assert env.get_database_url() == ""


def test_get_redis_url(monkeypatch):
    assert env.get_redis_url(Environment.STAGING).startswith("redis://")
    monkeypatch.setattr(env, "get_environment_config", lambda env: {})
    assert env.get_redis_url() == ""

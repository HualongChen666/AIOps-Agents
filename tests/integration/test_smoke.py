from core.integration_ecosystem import IntegrationEcosystem


def test_integration_ecosystem_smoke():
    ecosystem = IntegrationEcosystem()
    assert ecosystem.max_integrations == 100
    assert ecosystem.webhook_timeout == 30

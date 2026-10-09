import pytest
from unittest.mock import AsyncMock, patch
from custom_components.azae.const import DEFAULTS

@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield

@pytest.fixture
def account():
    return {"email": "client@example.invalid", "password": "synthetic-test-password",
            "code_agence": "0001", "matricule": "test-client"}

@pytest.fixture
def options():
    return dict(DEFAULTS)

@pytest.fixture
def mock_api():
    with patch("custom_components.azae.api.AzaeApi.login", new_callable=AsyncMock) as login, patch(
        "custom_components.azae.api.AzaeApi.hours", new_callable=AsyncMock, return_value=[]
    ) as hours:
        yield login, hours

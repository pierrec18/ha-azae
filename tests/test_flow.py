from unittest.mock import patch, AsyncMock
import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.azae.api import AuthError, ApiError
from custom_components.azae.model import SchemaError
from custom_components.azae.const import DOMAIN

async def test_user_and_duplicate(hass, account, options, mock_api):
    with patch("custom_components.azae.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {**account, "token_path": options["token_path"]})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert "token" not in result["data"]
        await hass.async_block_till_done()
        other = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER}, data={**account, "token_path": options["token_path"]})
        assert other["reason"] == "already_configured"

@pytest.mark.parametrize("error,key", [(AuthError(), "invalid_auth"), (ApiError(), "cannot_connect"), (SchemaError(), "unsupported_schema")])
async def test_login_errors(hass, account, options, mock_api, error, key):
    mock_api[0].side_effect = error
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER}, data={**account, "token_path": options["token_path"]})
    assert result["errors"]["base"] == key

async def test_options(hass, account, options, mock_api):
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {**options, "presence_mode": "pointage"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["presence_mode"] == "pointage"

@pytest.mark.parametrize("source,step,reason", [(config_entries.SOURCE_REAUTH, "reauth_confirm", "reauth_successful"), (config_entries.SOURCE_RECONFIGURE, "reconfigure", "reconfigure_successful")])
async def test_password_update_without_new_entry(hass, account, options, mock_api, source, step, reason):
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    with patch("homeassistant.config_entries.ConfigEntries.async_reload", new_callable=AsyncMock):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": source, "entry_id": entry.entry_id}, data=account if source == config_entries.SOURCE_REAUTH else None)
        assert result["step_id"] == step
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "replacement-test-password"})
        assert result["reason"] == reason
        assert entry.data["password"] == "replacement-test-password"
        assert len(hass.config_entries.async_entries(DOMAIN)) == 1

"""UI setup, options, reconfiguration and password reauthentication."""
import hashlib
import probatio as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
from .api import AzaeApi, ApiError, AuthError
from .const import DEFAULTS, DOMAIN
from .model import SchemaError, validate_options

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

def user_schema(values=None):
    values = values or {}
    return vol.Schema({
        vol.Required("email", default=values.get("email", "")): str,
        vol.Required("password"): PASSWORD,
        vol.Required("code_agence", default=values.get("code_agence", "")): str,
        vol.Required("matricule", default=values.get("matricule", "")): str,
        vol.Required("token_path", default=values.get("token_path", DEFAULTS["token_path"])): str,
    })

def options_schema(values):
    schema = {}
    for key, default in DEFAULTS.items():
        validator = str
        if key == "poll_seconds":
            validator = vol.All(vol.Coerce(int), vol.Range(min=60, max=3600))
        elif key == "evidence_hours":
            validator = vol.All(vol.Coerce(int), vol.Range(min=1, max=24))
        elif key == "presence_mode":
            validator = vol.In(["unknown", "pointage"])
        schema[vol.Required(key, default=values.get(key, default))] = validator
    return vol.Schema(schema)

async def validate_login(hass, data, token_path):
    if not all(isinstance(data.get(key), str) and data[key].strip() for key in ("email", "password", "code_agence", "matricule")):
        raise SchemaError("empty_input")
    await AzaeApi(async_get_clientsession(hass), data["email"], data["password"],
                  data["code_agence"], data["matricule"], token_path).login()

class AzaeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = {key: value for key, value in user_input.items() if key != "token_path"}
            data["email"] = data["email"].strip().lower()
            data["code_agence"] = data["code_agence"].strip()
            data["matricule"] = data["matricule"].strip()
            path = user_input["token_path"]
            try:
                validate_options({**DEFAULTS, "token_path": path})
                await validate_login(self.hass, data, path)
            except AuthError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            except SchemaError:
                errors["base"] = "unsupported_schema"
            else:
                identity = hashlib.sha256(
                    f"{data['email']}|{data['code_agence']}|{data['matricule']}".encode()
                ).hexdigest()
                await self.async_set_unique_id(identity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Azaé", data=data,
                                               options={**DEFAULTS, "token_path": path})
        return self.async_show_form(step_id="user", data_schema=user_schema(user_input), errors=errors)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, "password": user_input["password"]}
            try:
                await validate_login(self.hass, data, entry.options.get("token_path", DEFAULTS["token_path"]))
            except AuthError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            except SchemaError:
                errors["base"] = "unsupported_schema"
            else:
                return self.async_update_reload_and_abort(entry, data_updates=data)
        return self.async_show_form(step_id="reauth_confirm",
                                    data_schema=vol.Schema({vol.Required("password"): PASSWORD}), errors=errors)

    async def async_step_reconfigure(self, user_input=None):
        # Keep account/beneficiary identity stable; new account => new entry.
        return await self._reconfigure_password(user_input)

    async def _reconfigure_password(self, user_input):
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, "password": user_input["password"]}
            try:
                await validate_login(self.hass, data, entry.options.get("token_path", DEFAULTS["token_path"]))
            except AuthError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            except SchemaError:
                errors["base"] = "unsupported_schema"
            else:
                return self.async_update_reload_and_abort(entry, data_updates=data, reason="reconfigure_successful")
        return self.async_show_form(step_id="reconfigure",
                                    data_schema=vol.Schema({vol.Required("password"): PASSWORD}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AzaeOptionsFlow()

class AzaeOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate_options(user_input)
            except SchemaError:
                errors["base"] = "invalid_options"
            else:
                return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=options_schema(
            user_input or {**DEFAULTS, **self.config_entry.options}), errors=errors)

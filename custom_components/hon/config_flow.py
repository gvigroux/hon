
import logging
import voluptuous as vol

from .hon import HonConnection
from typing import Any

from homeassistant import config_entries

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
    CONN_CLASS_LOCAL_POLL,
)

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback

from .const import DOMAIN, CONF_ID_TOKEN, CONF_FRAMEWORK, CONF_COGNITO_TOKEN, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)


class HonFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL

    def __init__(self):
        self._email     = None
        self._password  = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is None:
            return self.async_show_form(step_id="user",data_schema=vol.Schema({vol.Required(CONF_EMAIL): str,vol.Required(CONF_PASSWORD): str}))

        self._email     = user_input[CONF_EMAIL]
        self._password  = user_input[CONF_PASSWORD]

        # Check if already configured
        await self.async_set_unique_id(self._email)
        self._abort_if_unique_id_configured()

        # Test connection
        hon = HonConnection(None, None, self._email, self._password)
        if( await hon.async_authorize() == False ):
            errors = {}
            errors["base"] = "auth_error"
            await hon.async_close()
            return self.async_show_form(step_id="user",data_schema=vol.Schema({vol.Required(CONF_EMAIL): str,vol.Required(CONF_PASSWORD): str}), errors=errors)
        await hon.async_close()

        return self.async_create_entry(
            title=self._email,
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_ID_TOKEN: "",
                CONF_FRAMEWORK: "none",
                CONF_COGNITO_TOKEN: "",
                CONF_REFRESH_TOKEN: ""
            },
        )

    async def async_step_import(self, user_input=None):
        """Import a config entry."""
        return await self.async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the reconfiguration flow."""
        #errors = {}
        #reconfig_entry = self._get_reconfigure_entry()

        if user_input is not None:
            #reconfigure_entry = self._get_reconfigure_entry()
            #self._email = reconfigure_entry.data[CONF_EMAIL]
            entry_id = self.context["entry_id"]
            #_LOGGER.error(f"entry_id: {entry_id}")
            #_LOGGER.error(self.context)

            # TODO: process user input
            #self.async_set_unique_id(self._email)
            #self._abort_if_unique_id_mismatch()

            config_entry = self.hass.config_entries.async_get_entry(entry_id)
                
            # Test connection
            hon = HonConnection(None, None, config_entry.unique_id, user_input[CONF_PASSWORD])
            if( await hon.async_authorize() == False ):
                errors = {}
                errors["base"] = "auth_error"
                await hon.async_close()
                return self.async_show_form(step_id="reconfigure",data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}), errors=errors)
            await hon.async_close()

            await self.async_set_unique_id(config_entry.unique_id)

            
            # Update the entry and reload without using `_get_reconfigure_entry()`
            #self.hass.config_entries.async_update_entry(
            #    config_entry,
            #    data={
            #        CONF_EMAIL: config_entry.unique_id,
            #        CONF_PASSWORD: user_input[CONF_PASSWORD],
            #        CONF_ID_TOKEN: "",
            #        CONF_FRAMEWORK: "none",
            #        CONF_COGNITO_TOKEN: "",
            #        CONF_REFRESH_TOKEN: ""
            #    },
            #)
            #await self.hass.config_entries.async_reload(entry_id)
            #return self.async_abort(reason="reconfigure_successful")

            #self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                entry=config_entry,
                unique_id=config_entry.unique_id,
                data={
                    CONF_EMAIL: config_entry.unique_id,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_ID_TOKEN: "",
                    CONF_FRAMEWORK: "none",
                    CONF_COGNITO_TOKEN: "",
                    CONF_REFRESH_TOKEN: ""
                },
                reason="reconfigure_successful"
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
        )
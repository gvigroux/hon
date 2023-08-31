
import logging
import voluptuous as vol

from .hon import HonConnection

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback

from .const import DOMAIN, CONF_ID_TOKEN, CONF_FRAMEWORK, CONF_COGNITO_TOKEN, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)


class HonFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        self._email     = None
        self._password  = None

    """
    def _show_setup_form(self, user_input=None, errors=None):

        if user_input is None:
            user_input = {}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")): str,
                }
            ),
            errors=errors or {},
        )
        """

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



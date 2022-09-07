import asyncio
import imp
import logging
import voluptuous as vol
import aiohttp
import asyncio
import json
import urllib.parse

from datetime import datetime
from dateutil.tz import gettz
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import HomeAssistantType


from .const import DOMAIN, PLATFORMS
from .hon import HonConnection, get_hOn_mac


_LOGGER = logging.getLogger(__name__)


HON_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(vol.All(cv.ensure_list, [HON_SCHEMA]))},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    hon = HonConnection(hass, entry)
    await hon.async_authorize()

    # Log all appliances
    _LOGGER.info(hon.appliances)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = hon

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    # Log details on unknown devices
    for appliance in hon.appliances:
        if appliance['applianceTypeId'] not in [2, 4, 6, 11]:
            try:
                status = await hon.async_get_state(appliance["macAddress"], appliance["applianceTypeName"], True)
            except:
                status = "Unable to get latest status"
            _LOGGER.warning("Unknown device detected [%s] with latest status [%s]", appliance, status)


    async def handle_oven_start(call):

        delay_time = 0
        tz = gettz(hass.config.time_zone)

        if "start" in call.data:
            date = datetime.strptime(call.data.get("start"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            delay_time = int((date - datetime.now(tz)).seconds / 60)

        if "end" in call.data and "duration" in call.data:
            date = datetime.strptime(call.data.get("end"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            duration = call.data.get("duration")
            delay_time = int((date - datetime.now(tz)).seconds / 60 - duration)

        paramaters = {
            "delayTime": delay_time,
            "onOffStatus": "1",
            "prCode": call.data.get("program"),
            "prPosition": "1",
            "recipeId": "NULL",
            "recipeStep": "1",
            "prTime": call.data.get("duration", "0"),
            "tempSel": call.data.get("temperature"),
            "preheatStatus": "1" if call.data.get("preheat", False) else "0",
        }

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "OV", paramaters)

    async def handle_oven_stop(call):

        parameters = {"onOffStatus": "0"}

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "OV", parameters)
    
    async def handle_cooler_lights_off(call):

        parameters = {"lightStatus": "0"}

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "WC", parameters)
        
    async def handle_cooler_lights_on(call):

        parameters = {"lightStatus": "1"}

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "WC", parameters)

    hass.services.async_register(DOMAIN, "turn_on_oven", handle_oven_start)
    hass.services.async_register(DOMAIN, "turn_off_oven", handle_oven_stop)
    hass.services.async_register(DOMAIN, "turn_off_cooler_lights", handle_cooler_lights_off)
    hass.services.async_register(DOMAIN, "turn_on_cooler_lights", handle_cooler_lights_on)
    
    return True

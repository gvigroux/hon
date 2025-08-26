import asyncio
import logging
import voluptuous as vol
import aiohttp
import json
import urllib.parse
import ast

from homeassistant.components.persistent_notification import create
from datetime import datetime
from dateutil.tz import gettz
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.core import HomeAssistant

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.template import device_id as get_device_id

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, PLATFORMS
from .hon import HonConnection, get_hOn_mac
from .device import HonDevice

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

# This method will update a sensor value with the targetted one for a better user experience
def update_sensor(hass, device_id, mac, sensor_name, state):
    entity_reg  = er.async_get(hass)
    entries     = er.async_entries_for_device(entity_reg, device_id)

    # Loop over all entries and update the good one
    for entry in entries:
        if( entry.unique_id == mac + '_' + sensor_name):
            inputStateObject = hass.states.get(entry.entity_id)
            hass.states.async_set(entry.entity_id, state, inputStateObject.attributes)

def get_parameters(call):
    parameters_str = call.data.get("parameters", "{}")
    if type(parameters_str) != str:
        parameters_str = str(parameters_str)
    return ast.literal_eval(parameters_str)

def get_device_ids(hass, call):
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    for entity_id in entity_ids:
        device_ids.append(get_device_id(hass, entity_id))
    return list(dict.fromkeys(device_ids))

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    from homeassistant.helpers import aiohttp_client
    
    try:
        hon = HonConnection(hass, entry)
        # Erstelle eine neue Session mit korrekten Headern
        session = aiohttp_client.async_get_clientsession(hass)
        
        # Erstelle eine neue Session mit benutzerdefinierten Headern
        headers = {
            'User-Agent': 'hOn/1.15.10 (com.haiereurope.hon; build:1.15.10; iOS 14.7.0) Alamofire/5.4.4',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Erstelle eine neue aiohttp Session mit den gewünschten Headern
        connector = session.connector
        timeout = session.timeout
        hon.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
        
        await hon.async_authorize()
        
    except Exception as e:
        _LOGGER.error(f"Authentication failed: {e}")
        # Fallback ohne spezielle Header
        try:
            hon = HonConnection(hass, entry)
            hon.session = aiohttp_client.async_get_clientsession(hass)
            await hon.async_authorize()
        except Exception as fallback_error:
            _LOGGER.error(f"Fallback authentication also failed: {fallback_error}")
            raise fallback_error

    # Log all appliances
    _LOGGER.debug(f"Appliances: {hon.appliances}")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = hon

    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)
        coordinator.device = HonDevice(hon, coordinator, appliance)
        await coordinator.async_config_entry_first_refresh()

        await coordinator.device.load_commands()
        await coordinator.device.load_statistics()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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

        parameters = {
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
        return await hon.async_set(mac, "OV", parameters)

    async def handle_dishwasher_start(call):
        delay_time = 0
        tz = gettz(hass.config.time_zone)

        if "start" in call.data:
            date = datetime.strptime(call.data.get("start"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            delay_time = int((date - datetime.now(tz)).seconds / 60)

        if "end" in call.data and "duration" in call.data:
            date = datetime.strptime(call.data.get("end"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            duration = call.data.get("duration")
            delay_time = int((date - datetime.now(tz)).seconds / 60 - duration)

        parameters = {
            "delayTime": delay_time,
            "onOffStatus": "1",
            "prCode": call.data.get("program"),
            "prPosition": "1",
            "prTime": call.data.get("duration", "0"),
        }

        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "DW", parameters)
    
    async def handle_washingmachine_start(call):
        delay_time = 0
        tz = gettz(hass.config.time_zone)
        if "end" in call.data:
            date = datetime.strptime(call.data.get("end"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            delay_time = int((date - datetime.now(tz)).seconds / 60)

        parameters = {
            "haier_MainWashSpeed": "50",
            "creaseResistSoakStatus": "0",
            "haier_SoakPrewashSelection": "0",
            "prCode": "999",
            "soakWashStatus": "0",
            "strongStatus": "0",
            "energySavingStatus": "0",
            "spinSpeed": call.data.get("spinSpeed", "400"),
            "haier_MainWashWaterLevel": "2",
            "rinseIterationTime": "8",
            "haier_SoakPrewashSpeed": "0",
            "permanentPressStatus": "1",
            "nightWashStatus": "0",
            "intelligenceStatus": "0",
            "haier_SoakPrewashStopTime": "0",
            "weight": "5",
            "highWaterLevelStatus": "0",
            "voiceStatus": "0",
            "haier_SoakPrewashTime": "0",
            "autoDisinfectantStatus": "0",
            "cloudProgSrc": "2",
            "haier_SoakPrewashRotateTime": "0",
            "cloudProgId": "255",
            "haier_SoakPrewashTemperature": "0",
            "dryProgFlag": "0",
            "dryLevel": "0",
            "haier_RinseRotateTime": "20",
            "uvSterilizationStatus": "0",
            "dryTime": "0",
            "delayStatus": "0",
            "dryLevelAllowed": "0",
            "rinseIterations": call.data.get("rinseIterations", "2"),
            "lockStatus": "0",
            "mainWashTime": call.data.get("mainWashTime", "15"),
            "autoSoftenerStatus": call.data.get("autoSoftenerStatus", "0"),
            "washerDryIntensity": "1",
            "autoDetergentStatus": "0",
            "antiAllergyStatus": "0",
            "speedUpStatus": "0",
            "temp": call.data.get("temp", "30"),
            "haier_MainWashRotateTime": "20",
            "detergentBStatus": "0",
            "haier_MainWashStopTime": "5",
            "texture": "1",
            "operationName": "grOnlineWash",
            "haier_RinseSpeed": "50",
            "haier_ConstantTempStatus": "1",
            "haier_RinseStopTime": "5",
            "delayTime": delay_time
        }

        mac = get_hOn_mac(call.data.get("device"), hass)
        json_data = await hon.async_get_state(mac, "WM")

        if json_data["category"] != "DISCONNECTED":
            return await hon.async_set(mac, "WM", parameters)
        _LOGGER.error(f"This hOn device is disconnected - Mac address [{mac}]")

    async def handle_purifier_start(call):
        parameters = {
            "onOffStatus": "1",
            "machMode": "2",
        }

        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "AP", parameters)

    async def handle_purifier_maxmode(call):
        parameters = { "machMode": "4" }
        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "AP", parameters)

    async def handle_purifier_automode(call):
        parameters = { "machMode": "2" }
        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "AP", parameters)

    async def handle_purifier_sleepmode(call):
        parameters = { "machMode": "1" }
        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "AP", parameters)

    # Generic method to set a mode to any hOn device
    async def handle_set_mode(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"onOffStatus": "1", "machMode": call.data.get("mode", 1)}
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()

    # Generic method to TURN OFF any hOn device
    async def handle_turn_off(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        
        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"onOffStatus": "0", "machMode": "1" }
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()

    async def handle_light_on(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)

        update_sensor(hass, device_id, mac, "light_status" , "on")
        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"lightStatus": "1"})
        await coordinator.async_request_refresh()

    async def handle_light_off(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        update_sensor(hass, device_id, mac, "light_status" , "off")

        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"lightStatus": "0"})
        await coordinator.async_request_refresh()

    async def handle_health_mode_on(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        update_sensor(hass, device_id, mac, "health_mode" , "on")

        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"healthMode": "1"})
        await coordinator.async_request_refresh()

    async def handle_health_mode_off(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        update_sensor(hass, device_id, mac, "health_mode" , "off")

        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"healthMode": "0"})
        await coordinator.async_request_refresh()

    async def handle_start_program(call):
        device_ids = get_device_ids(hass, call)
        
        for device_id in device_ids:
            device      = hon.get_device(hass, device_id)
            command     = device.commands.get("startProgram")
            programs    = command.get_programs()
            program     = call.data.get("program")
            if( program not in programs.keys()):
                keys = ", ".join(programs)
                raise HomeAssistantError(f"Invalid [Program] value, allowed values [{keys}]")

            parameters  = get_parameters(call)
            await device.start_command(program, parameters).send()

    async def handle_custom_request(call):
        device_ids = get_device_ids(hass, call)
        parameters = get_parameters(call)
        for device_id in device_ids:
            device = hon.get_device(hass, device_id)
            await device.coordinator.async_set(parameters)
            await device.coordinator.async_request_refresh()

    async def handle_update_settings(call):
        device_ids = get_device_ids(hass, call)
        parameters = get_parameters(call)

        for device_id in device_ids:
            device = hon.get_device(hass, device_id)
            await device.settings_command(parameters).send()

    hass.services.async_register(DOMAIN, "turn_on_washingmachine", handle_washingmachine_start)
    hass.services.async_register(DOMAIN, "turn_on_oven", handle_oven_start)
    hass.services.async_register(DOMAIN, "turn_on_dishwasher", handle_dishwasher_start)
    hass.services.async_register(DOMAIN, "turn_on_purifier", handle_purifier_start)
    hass.services.async_register(DOMAIN, "set_auto_mode_purifier", handle_purifier_automode)
    hass.services.async_register(DOMAIN, "set_sleep_mode_purifier", handle_purifier_sleepmode)
    hass.services.async_register(DOMAIN, "set_max_mode_purifier", handle_purifier_maxmode)

    hass.services.async_register(DOMAIN, "set_mode", handle_set_mode)
    hass.services.async_register(DOMAIN, "turn_off", handle_turn_off)
    hass.services.async_register(DOMAIN, "turn_light_on",   handle_light_on)
    hass.services.async_register(DOMAIN, "turn_light_off",  handle_light_off)
    hass.services.async_register(DOMAIN, "send_custom_request",  handle_custom_request)
    hass.services.async_register(DOMAIN, "climate_turn_health_mode_on",   handle_health_mode_on)
    hass.services.async_register(DOMAIN, "climate_turn_health_mode_off",  handle_health_mode_off)

    hass.services.async_register(DOMAIN, "start_program",   handle_start_program)
    hass.services.async_register(DOMAIN, "update_settings", handle_update_settings)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Schließe die Session ordnungsgemäß
        hon = hass.data[DOMAIN].get(entry.unique_id)
        if hon and hasattr(hon, 'session') and hon.session:
            await hon.session.close()
        hass.data[DOMAIN].pop(entry.unique_id)
    return unload_ok

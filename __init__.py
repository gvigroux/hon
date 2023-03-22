import asyncio
import imp
import logging
import voluptuous as vol
import aiohttp
import asyncio
import json
import urllib.parse
import ast

from datetime import datetime
from dateutil.tz import gettz
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_component as ec


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


def update_sensor(hass, device_id, mac, sensor_name, state):

    entity_reg  = er.async_get(hass)
    entries     = er.async_entries_for_device(entity_reg, device_id)

    # Loop over all entries and update the good ones
    for entry in entries:
        if( entry.unique_id == mac + '_' + sensor_name):
            inputStateObject = hass.states.get(entry.entity_id)
            hass.states.async_set(entry.entity_id, state, inputStateObject.attributes)


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
    #for appliance in hon.appliances:

        #if appliance.get("macAddress", None) == None:
        #    continue

        #if appliance['applianceTypeId'] not in [1, 2, 4, 6, 7, 8, 9, 11, 14]:
        #    try:
        #        status = await hon.async_get_state(appliance["macAddress"], appliance["applianceTypeName"], True)
        #    except:
        #        status = "Unable to get latest status"
        #    _LOGGER.warning("Unknown device detected [%s] with latest status [%s]", appliance, status)


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

        paramaters = {
            "delayTime": delay_time,
            "onOffStatus": "1",
            "prCode": call.data.get("program"),
            "prPosition": "1",
            "prTime": call.data.get("duration", "0"),
 #           "extraDry": "1" if call.data.get("extra_dry", False) else "0",
 #           "openDoor": "1" if call.data.get("open_door", False) else "0", ##conditional program
 #           "halfLoad": "1" if call.data.get("half_load", False) else "0", ##conditional programm
 #           "prStrDisp": call.data.get("string_display"),
        }

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "DW", paramaters)
    
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

        json = await hon.async_get_state(mac, "WM", True)

        if json["payload"]["lastConnEvent"]["category"] != "DISCONNECTED":
            return await hon.async_set(mac, "WM", parameters)
        else:
            _LOGGER.error(
                    "This hOn device is disconnected - Mac address ["
                    + mac
                    + "]"
                )
        
    async def handle_washingmachine_stop(call):

        parameters = {"onOffStatus":"0"}
        
        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "WM", parameters)

    async def handle_purifier_stop(call):

        parameters = {"onOffStatus": "0"}

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "AP", parameters)

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
        #parameters = {"onOffStatus": "1", "machMode": call.data.get("mode", 1)}
        #return await hon.async_set_parameter(call.data.get("device_id")[0], parameters)
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"onOffStatus": "1", "machMode": call.data.get("mode", 1)}
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()

    # Generic method to TURN OFF any hOn device
    async def handle_turn_off(call):
        #parameters = {"onOffStatus": "0", "machMode": "1" }
        #return await hon.async_set_parameter(call.data.get("device_id")[0], parameters)
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"onOffStatus": "0", "machMode": "1" }
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()

    async def handle_light_on(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"lightStatus": "1"}
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()


        #entity_registry = er.async_get(hass)
        #entries         = er.async_entries_for_device(entity_registry, device_id)

        #for entry in entries:
        #    _LOGGER.warning(entry.entity_id)
        #    parameters  = {"lightStatus": "1"}
        #    await entity.async_set(parameters)
        #    break
        #
        #device_registry = dr.async_get(hass)
        #device = device_registry.async_get(device_id)
        #identifiers = next(iter(device.identifiers))
        #

        #mac         = identifiers[1]
        #type_name   = identifiers[2]

        #parameters  = {"lightStatus": "1"}
        #await hon.async_set(mac, type_name, parameters)

        #update_sensor(hass, device_id, mac, "light_status" , "on")

        #return await hon.async_set_parameter(call.data.get("device_id")[0], parameters)

    async def handle_light_off(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"lightStatus": "1"}
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()

        #device_id = call.data.get("device_id")[0]

        #
        #device_registry = dr.async_get(hass)
        #device = device_registry.async_get(device_id)
        #identifiers = next(iter(device.identifiers))
        #

        #mac         = identifiers[1]
        #type_name   = identifiers[2]

        #parameters  = {"lightStatus": "0"}
        #await hon.async_set(mac, type_name, parameters)

        #update_sensor(hass, device_id, mac, "light_status" , "off")
        
        #update_sensor(hass, call, "light_status" , "on")
        #parameters = {"lightStatus": "0"}
        #hass.async_create_task(update_sensor(hass, call, "light_status" , "off"))

        #update_sensor(hass, call, "light_status" , "off")
        #return await hon.async_set_parameter(call.data.get("device_id")[0], parameters)


    async def handle_custom_request(call):
        _LOGGER.warning(call)
        #device_id = call.data.get("device")
        #mac = get_hOn_mac(device_id, hass)
        #coordinator = await hon.async_get_existing_coordinator(mac)
        #parameters = {"lightStatus": "1"}
        #await coordinator.async_set(parameters)
        #await coordinator.async_request_refresh()

        parameters_str = call.data.get("parameters")
        _LOGGER.warning(parameters_str)
        #parameters_str = parameters_str.strip("{}")
        #parameters = dict(map(str.strip, sub.split(':', 1))
        #                    for sub in parameters_str.split(', ') if ':' in sub)

        #parameters = json.loads(parameters_str)
        parameters = ast.literal_eval(parameters_str)
        # printing result
        _LOGGER.warning("The converted dictionary is : " + str(parameters))

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

    #hass.services.async_register(DOMAIN, "turn_off_oven", handle_oven_stop)
    #hass.services.async_register(DOMAIN, "turn_off_purifier", handle_purifier_stop)
    #hass.services.async_register(DOMAIN, "turn_off_cooler_lights", handle_cooler_lights_off)
    #hass.services.async_register(DOMAIN, "turn_on_cooler_lights", handle_cooler_lights_on)
    #hass.services.async_register(DOMAIN, "turn_off_washingmachine", handle_washingmachine_stop)
    return True

import logging
import asyncio
import json
from datetime import datetime, timedelta, timezone
from dateutil.tz import gettz
from typing import Optional
from enum import IntEnum

from .const import DOMAIN, OVEN_PROGRAMS, DISH_WASHER_MODE, DISH_WASHER_PROGRAMS, CLIMATE_MODE, APPLIANCE_TYPE
from .base import HonBaseCoordinator, HonBaseEntity, HonBaseBinarySensorEntity

from homeassistant.core import callback
from homeassistant.helpers import entity_platform
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        
        if appliance.get("macAddress", None) == None:
            _LOGGER.warning("Appliance with no MAC")
            continue

        # Get or Create Coordinator
        coordinator = await hon.async_get_coordinator(appliance)
        await coordinator.async_config_entry_first_refresh()

        # Every device should have a OnOff status
        appliances.extend([HonBaseOnOff(hass, coordinator, entry, appliance)])

        if( "doorStatusZ1" in coordinator.data ):
            appliances.extend([HonBaseDoorStatus(hass, coordinator, entry, appliance, "Z1", "Zone 1")])
        if( "doorStatusZ2" in coordinator.data ):
            appliances.extend([HonBaseDoorStatus(hass, coordinator, entry, appliance, "Z2", "Zone 2")])
        if( "doorLockStatus" in coordinator.data ):
            appliances.extend([HonBaseDoorLockStatus(hass, coordinator, entry, appliance)])

        if( "lockStatus" in coordinator.data ):
            appliances.extend([HonBaseChildLockStatus(hass, coordinator, entry, appliance)])


        if( "lightStatus" in coordinator.data ):
            appliances.extend([HonBaseLightStatus(hass, coordinator, entry, appliance)])
        if( "remoteCtrValid" in coordinator.data ):
            appliances.extend([HonBaseRemoteControl(hass, coordinator, entry, appliance)])
        if( "preheatStatus" in coordinator.data ):
            appliances.extend([HonBasePreheating(hass, coordinator, entry, appliance)])




    async_add_entities(appliances)

    platform = entity_platform.async_get_current_platform()
    #platform.async_register_entity_service("turn_lights_on",{},"async_set_on",)
    #platform.async_register_entity_service("turn_lights_off",{},"async_set_off",)



class HonBaseOnOff(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "onOffStatus", "Status")

        self._attr_device_class = BinarySensorDeviceClass.POWER

    def coordinator_update(self):
        if( "onOffStatus" in self._coordinator.data ):
            self._attr_is_on = self._coordinator.data["onOffStatus"]["parNewVal"] == "1"
        else:
            self._attr_is_on = self._coordinator.data["category"] == "CONNECTED"



class HonBaseDoorStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone, zone_name) -> None:
        super().__init__(coordinator, appliance, "doorStatus" + zone, f"Door status {zone_name}")

        self._attr_device_class = BinarySensorDeviceClass.DOOR



class HonBaseLightStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "lightStatus", "Light")

        self._attr_device_class = BinarySensorDeviceClass.LIGHT
        self._attr_icon = "mdi:lightbulb"

    #async def async_set_on(self):
    #    parameters  = {"lightStatus": "1"}
    #    await self.async_set(parameters)
    #    self._attr_is_on = True
    #    self.async_write_ha_state()

    #async def async_set_off(self):
    #    parameters  = {"lightStatus": "0"}
    #    await self.async_set(parameters)
    #    self._attr_is_on = False
    #    self.async_write_ha_state()
    


class HonBaseRemoteControl(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "remoteCtrValid", "Remote Control")

        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:remote"


class HonBaseDoorLockStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "doorLockStatus", "Door Lock")

        self._attr_device_class = BinarySensorDeviceClass.LOCK

    def coordinator_update(self):
        self._attr_is_on = self._coordinator.data["doorLockStatus"]["parNewVal"] == "0"


class HonBaseChildLockStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "lockStatus", "Child Lock")

        self._attr_device_class = BinarySensorDeviceClass.LOCK

    def coordinator_update(self):
        self._attr_is_on = self._coordinator.data["lockStatus"]["parNewVal"] == "0"


class HonBasePreheating(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "preheatStatus", "Preheating")

        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:thermometer-chevron-up"


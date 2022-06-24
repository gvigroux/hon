import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from enum import IntEnum

from homeassistant.const import TEMP_CELSIUS, TIME_MINUTES

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

from homeassistant.core import callback


from .const import DOMAIN, OVEN_PROGRAMS

from .oven import HonOvenEntity, HonOvenCoordinator

from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        if appliance["applianceTypeId"] == 4:
            coordinator = HonOvenCoordinator(hass, hon, appliance)
            await coordinator.async_config_entry_first_refresh()

            appliances.extend(
                [
                    HonOvenTemperature(hass, coordinator, entry, appliance),
                    HonOvenTargetTemperature(hass, coordinator, entry, appliance),
                    HonOvenProgramDuration(hass, coordinator, entry, appliance),
                    HonOvenRemaining(hass, coordinator, entry, appliance),
                    HonOvenPreheating(hass, coordinator, entry, appliance),
                    HonOvenRemoteControl(hass, coordinator, entry, appliance),
                    HonOvenOnOff(hass, coordinator, entry, appliance),
                    HonOvenProgram(hass, coordinator, entry, appliance),
                ]
            )
            await coordinator.async_request_refresh()

    async_add_entities(appliances)


class HonOvenTemperature(SensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_temperature"
        self._attr_name = f"{self._name} Temperature"
        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = json["temp"]["parNewVal"]
        self.async_write_ha_state()


class HonOvenTargetTemperature(SensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_target_temperature"
        self._attr_name = f"{self._name} Target Temperature"
        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = json["tempSel"]["parNewVal"]
        self.async_write_ha_state()


class HonOvenPreheating(BinarySensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_preheating"
        self._attr_name = f"{self._name} Preheating"
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:thermometer-chevron-up"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_is_on = json["preheatStatus"]["parNewVal"] == "1"
        self.async_write_ha_state()


class HonOvenProgramDuration(SensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_duration"
        self._attr_name = f"{self._name} Program Duration"
        self._attr_native_unit_of_measurement = TIME_MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timelapse"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = json["prTime"]["parNewVal"]
        self.async_write_ha_state()


class HonOvenRemaining(SensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_remaining"
        self._attr_name = f"{self._name} Time Remaining"
        self._attr_native_unit_of_measurement = TIME_MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:progress-clock"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = json["remainingTimeMM"]["parNewVal"]
        self.async_write_ha_state()


class HonOvenProgram(SensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_program"
        self._attr_name = f"{self._name} Program"
        self._attr_icon = "mdi:chef-hat"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        program = self._attr_is_on = json["prCode"]["parNewVal"]

        if program in OVEN_PROGRAMS:
            self._attr_native_value = OVEN_PROGRAMS[program]
        else:
            self._attr_native_value = f"Unkwon program {program}"

        self.async_write_ha_state()


class HonOvenRemoteControl(BinarySensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_remote"
        self._attr_name = f"{self._name} Remote Control"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:remote"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_is_on = json["remoteCtrValid"]["parNewVal"] == "1"
        self.async_write_ha_state()


class HonOvenOnOff(BinarySensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_on_off"
        self._attr_name = f"{self._name}"
        self._attr_device_class = BinarySensorDeviceClass.POWER
        self._attr_icon = "mdi:toaster-oven"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_is_on = json["onOffStatus"]["parNewVal"] == "1"
        self.async_write_ha_state()

import logging
import asyncio
import json
from datetime import datetime, timedelta, timezone
from dateutil.tz import gettz
from typing import Optional
from enum import IntEnum

from sqlalchemy import null

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


from .const import DOMAIN, OVEN_PROGRAMS, WASHING_MACHINE_MODE

from .oven import HonOvenEntity, HonOvenCoordinator
from .washing_machine import HonWashingMachineCoordinator, HonWashingMachineEntity

from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        if appliance["applianceTypeId"] == 1:
            coordinator = HonWashingMachineCoordinator(hass, hon, appliance)
            await coordinator.async_config_entry_first_refresh()

            appliances.extend(
                [
                    HonWashingMachineTimeRemaining(hass, coordinator, entry, appliance),
                    HonWashingMachineMode(hass, coordinator, entry, appliance),
                ]
            )

            await coordinator.async_request_refresh()
        elif appliance["applianceTypeId"] == 4:
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
                    HonOvenEnd(hass, coordinator, entry, appliance),
                    HonOvenStart(hass, coordinator, entry, appliance),
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

        self._attr_native_value = int(json["remainingTimeMM"]["parNewVal"]) + int(
            json["delayTime"]["parNewVal"]
        )
        self.async_write_ha_state()


class HonOvenEnd(SensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_end"
        self._attr_name = f"{self._name} End Time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-end"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        delay = int(json["delayTime"]["parNewVal"])
        remaining = int(json["remainingTimeMM"]["parNewVal"])

        if remaining == 0:
            self._attr_native_value = None
            self.async_write_ha_state()
            return

        self._attr_available = True
        self._attr_native_value = datetime.now(timezone.utc).replace(
            second=0
        ) + timedelta(minutes=delay + remaining)
        self.async_write_ha_state()


class HonOvenStart(SensorEntity, HonOvenEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_start"
        self._attr_name = f"{self._name} Start Time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-start"
        self._on = False

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        previous = self._on
        self._on = json["onOffStatus"]["parNewVal"] == "1"

        delay = int(json["delayTime"]["parNewVal"])

        if delay == 0:
            if self._on is True and previous is False:
                self._attr_native_value = datetime.now(timezone.utc).replace(second=0)
            elif self._on is False:
                self._attr_native_value = None

        else:
            self._attr_native_value = datetime.now(timezone.utc).replace(
                second=0
            ) + timedelta(minutes=delay)


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

        program = json["prCode"]["parNewVal"]

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


class HonWashingMachineMode(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_machine_mode"
        self._attr_name = f"{self._name} Machine Mode"
        self._attr_icon = "mdi:chef-hat"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        mode = json["machMode"]

        if mode in WASHING_MACHINE_MODE:
            self._attr_native_value = WASHING_MACHINE_MODE[mode]
        else:
            self._attr_native_value = f"Unknown mode {mode}"

        self.async_write_ha_state()


class HonWashingMachineTimeRemaining(SensorEntity, HonWashingMachineEntity):
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

        self._attr_native_value = int(json["remainingTimeMM"]["parNewVal"]) + int(
            json["delayTime"]["parNewVal"]
        )
        self.async_write_ha_state()

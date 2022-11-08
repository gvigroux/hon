from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

from homeassistant.const import TIME_MINUTES
from homeassistant.core import callback

import logging
from datetime import timedelta
from .const import DOMAIN


import logging
from datetime import timedelta
from .const import DOMAIN, TUMBLE_DRYER_MODE, TUMBLE_DRYER_PROGRAMS, TUMBLE_DRYER_PROGRAMS_PHASE, TUMBLE_DRYER_DRYL, TUMBLE_DRYER_TEMPL


_LOGGER = logging.getLogger(__name__)


class HonTumbleDryerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, hon, appliance):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="hOn Tumble dryer",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )
        self._hon = hon
        self._mac = appliance["macAddress"]
        self._type_name = appliance["applianceTypeName"]

    async def _async_update_data(self):
        return await self._hon.async_get_state(self._mac, self._type_name)


class HonTumbleDryerEntity(CoordinatorEntity):
    def __init__(self, hass, entry, coordinator, appliance) -> None:
        super().__init__(coordinator)

        self._hon = hass.data[DOMAIN][entry.unique_id]
        self._hass = hass
        self._brand = appliance["brand"]

        if "nickName" in appliance:
            self._name = appliance["nickName"]
        else:
            self._name = "Tumble dryer"

        self._mac = appliance["macAddress"]
        self._connectivity = appliance["connectivity"]
        self._model = appliance["modelName"]
        self._series = appliance["series"]
        self._model_id = appliance["applianceModelId"]
        self._type_name = appliance["applianceTypeName"]
        self._serial_number = appliance["serialNumber"]
        self._fw_version = appliance["fwVersion"]

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._mac)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }

class HonTumbleDryerMode(SensorEntity, HonTumbleDryerEntity):
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

        mode = json["machMode"]["parNewVal"]

        if mode in TUMBLE_DRYER_MODE:
            self._attr_native_value = TUMBLE_DRYER_MODE[mode]
        else:
            self._attr_native_value = f"Unknown mode {mode}"

        self.async_write_ha_state()

class HonTumbleDryerStart(SensorEntity, HonTumbleDryerEntity):
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

class HonTumbleDryerTimeRemaining(SensorEntity, HonTumbleDryerEntity):
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

class HonTumbleDryerProgram(SensorEntity, HonTumbleDryerEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_program"
        self._attr_name = f"{self._name} Program"
        self._attr_icon = "mdi:tumble-dryer"
        self._attr_device_class = "tumbledryerprogram"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        program = json["prCode"]["parNewVal"]

        if program in TUMBLE_DRYER_PROGRAMS:
            self._attr_native_value = TUMBLE_DRYER_PROGRAMS[program]
        else:
            self._attr_native_value = f"Unknown program {program}"

        self.async_write_ha_state()

class HonTumbleDryerProgramPhase(SensorEntity, HonTumbleDryerEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_program_phase"
        self._attr_name = f"{self._name} Program Phase"
        self._attr_icon = "mdi:tumble-dryer"
        self._attr_device_class = "tumbledryerprogramphase"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        programPhase = json["prPhase"]["parNewVal"]

        if programPhase in TUMBLE_DRYER_PROGRAMS_PHASE:
            self._attr_native_value = TUMBLE_DRYER_PROGRAMS_PHASE[programPhase]
        else:
            self._attr_native_value = f"Unknown program phase {programPhase}"

        self.async_write_ha_state()

class HonTumbleDryerDryLevel(SensorEntity, HonTumbleDryerEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_drylevel"
        self._attr_name = f"{self._name} Dry level"
        self._attr_icon = "mdi:hair-dryer"
        self._attr_device_class = "tumbledryerdrylevel"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        drylevel = json["dryLevel"]["parNewVal"]

        if drylevel in TUMBLE_DRYER_DRYL:
            self._attr_native_value = TUMBLE_DRYER_DRYL[drylevel]
        else:
            self._attr_native_value = f"Unknown dry level {drylevel}"

        self.async_write_ha_state()

class HonTumbleDryerTempLevel(SensorEntity, HonTumbleDryerEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_templevel"
        self._attr_name = f"{self._name} Temperature level"
        self._attr_icon = "mdi:thermometer"
        self._attr_device_class = "tumbledryertemplevel"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        templevel = json["tempLevel"]["parNewVal"]

        if templevel in TUMBLE_DRYER_TEMPL:
            self._attr_native_value = TUMBLE_DRYER_TEMPL[templevel]
        else:
            self._attr_native_value = f"Unknown Temperature level {templevel}"

        self.async_write_ha_state()
		
class HonTumbleDryerOnOff(BinarySensorEntity, HonTumbleDryerEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_on_off"
        self._attr_name = f"{self._name}"
        self._attr_device_class = BinarySensorDeviceClass.POWER
        self._attr_icon = "mdi:tumble-dryer-off"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_is_on = json["onOffStatus"]["parNewVal"] == "1"
        self.async_write_ha_state()

class HonTumbleDryerRemoteControl(BinarySensorEntity, HonTumbleDryerEntity):
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

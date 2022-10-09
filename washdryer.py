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
from .const import DOMAIN, WASHING_MACHINE_MODE


_LOGGER = logging.getLogger(__name__)


class HonWashDryerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, hon, appliance):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="hOn WashDryer",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )
        self._hon = hon
        self._mac = appliance["macAddress"]
        self._type_name = appliance["applianceTypeName"]

    async def _async_update_data(self):
        return await self._hon.async_get_state(self._mac, self._type_name)


class HonWashDryerEntity(CoordinatorEntity):
    def __init__(self, hass, entry, coordinator, appliance) -> None:
        super().__init__(coordinator)

        self._hon = hass.data[DOMAIN][entry.unique_id]
        self._hass = hass
        self._brand = appliance["brand"]

        if "nickName" in appliance:
            self._name = appliance["nickName"]
        else:
            self._name = "WashDryer"

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

class HonWashDryerMode(SensorEntity, HonWashDryerEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_machine_mode"
        self._attr_name = f"{self._name} Machine Mode"
        self._attr_icon = "mdi:washing-machine"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        mode = json["machMode"]["parNewVal"]

        if mode in WASHING_MACHINE_MODE:
            self._attr_native_value = WASHING_MACHINE_MODE[mode]
        else:
            self._attr_native_value = f"Unknown mode {mode}"

        self.async_write_ha_state()


class HonWashDryerTimeRemaining(SensorEntity, HonWashDryerEntity):
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

class HonWashDryerRemoteControl(BinarySensorEntity, HonWashDryerEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_remote_on_off"
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

        self._attr_is_on = json["remoteCtrValid"]["parNewVal"] == 1
        self.async_write_ha_state()
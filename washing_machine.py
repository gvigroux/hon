from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)


import logging
from datetime import timedelta
from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


class HonWashingMachineCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, hon, appliance):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="hOn Washing Machine",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )
        self._hon = hon
        self._mac = appliance["macAddress"]
        self._type_name = appliance["applianceTypeName"]

    async def _async_update_data(self):
        return await self._hon.async_get_state(self._mac, self._type_name)


class HonWashingMachineEntity(CoordinatorEntity):
    def __init__(self, hass, entry, coordinator, appliance) -> None:
        super().__init__(coordinator)

        self._hon = hass.data[DOMAIN][entry.unique_id]
        self._hass = hass
        self._brand = appliance["brand"]

        if "nickName" in appliance:
            self._name = appliance["nickName"]
        else:
            self._name = "Washing Machine"

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

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from homeassistant.components.binary_sensor import (
    BinarySensorEntity
)

from homeassistant.core import callback
import logging
import re
from datetime import timedelta
from .const import DOMAIN, APPLIANCE_DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

class HonBaseCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, hon, appliance):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="hOn Device",
            update_interval=timedelta(seconds=30),
        )
        self._hon       = hon
        self._mac       = appliance["macAddress"]
        self._type_name = appliance["applianceTypeName"]

    async def _async_update_data(self):
        return await self._hon.async_get_state(self._mac, self._type_name)

    async def async_set(self, parameters):
        await self._hon.async_set(self._mac, self._type_name, parameters)
        
    def has_int_data(self, key):
        if self.data is False:
            return False
        if key not in self.dataFalse:
            return False
        if( int(data[key]["parNewVal"]) > 0 ):
            return True
        return False

    def get(self, key):
        return self.data.get(key, "")

    def addKey(self, key):
        _LOGGER.warning(key)


class HonBaseEntity(CoordinatorEntity):
    def __init__(self, hass, entry, coordinator, appliance) -> None:
        super().__init__(coordinator)

        self._hon       = hass.data[DOMAIN][entry.unique_id]
        self._hass      = hass
        self._brand     = appliance["brand"]
        self._type_name = appliance["applianceTypeName"]
        self._type_id = appliance["applianceTypeId"]
        self._name      = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._mac       = appliance["macAddress"]
        self._connectivity = appliance["connectivity"]
        self._model         = appliance["modelName"]
        self._series        = appliance["series"]
        self._model_id      = appliance["applianceModelId"]
        self._serial_number = appliance["serialNumber"]
        self._fw_version    = appliance["fwVersion"]

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }

    async def async_set(self, parameters):
        await self._hon.async_set(self._mac, self._type_name, parameters)


class HonBaseBinarySensorEntity(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, appliance, key, sensor_name) -> None:
        _LOGGER.warning(coordinator)
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._coordinator.addKey(key)
        self._mac           = appliance["macAddress"]
        self._type_id       = appliance["applianceTypeId"]
        self._name          = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._brand         = appliance["brand"]
        self._model         = appliance["modelName"]
        self._fw_version    = appliance["fwVersion"]
        self._type_name     = appliance["applianceTypeName"]

        #Generate unique ID from key
        self._attr_unique_id = self._mac + "_" + re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        _LOGGER.error(self._attr_unique_id)
        self._attr_name = self._name + " " + sensor_name

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return
        self.coordinator_update()
        self.async_write_ha_state()
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from homeassistant.components.binary_sensor import ( BinarySensorEntity )
from homeassistant.components.sensor import ( SensorEntity )
from homeassistant.components.switch import SwitchEntityDescription, SwitchEntity


from homeassistant.core import callback
import logging
import re
from datetime import timedelta
from .const import DOMAIN, APPLIANCE_DEFAULT_NAME
from .command import HonCommand

_LOGGER = logging.getLogger(__name__)

class HonBaseCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, hon, appliance):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="hOn Device",
            update_interval=timedelta(seconds=60),
        )
        self._hon       = hon
        self._device    = None
        self._appliance = appliance

        try:
            self._mac           = appliance["macAddress"]
            self._type_name     = appliance["applianceTypeName"]
            self._type_id       = appliance["applianceTypeId"]
            self._name          = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
            self._brand         = appliance["brand"]
            self._model         = appliance["modelName"]
            self._fw_version    = appliance["fwVersion"]
        except:
            _LOGGER.warning(f"Invalid appliance data in {appliance}" )


    async def _async_update_data(self):
        #data = await self._hon.async_get_context(self._device)
        await self._device.load_context()

        #data = await self._hon.async_get_state(self._mac, self._type_name)
        #if( self._device != None ):
        #    self._device.load_context(data)
        #return data

    @property
    def device(self):
        return self._device


    @device.setter
    def device(self, value):
        self._device = value

    async def async_set(self, parameters):
        await self._hon.async_set(self._mac, self._type_name, parameters)
        
    def get(self, key):
        return self.data.get(key, "")


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

class HonBaseBinarySensorEntity(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, appliance, key, sensor_name) -> None:
        super().__init__(coordinator)
        self._coordinator   = coordinator
        self._mac           = appliance["macAddress"]
        self._type_id       = appliance["applianceTypeId"]
        self._name          = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._brand         = appliance["brand"]
        self._model         = appliance["modelName"]
        self._fw_version    = appliance["fwVersion"]
        self._type_name     = appliance["applianceTypeName"]
        self._key           = key
        self._device        = coordinator.device

        #Generate unique ID from key
        key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        if( len(key_formatted) <= 0 ): 
            key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', sensor_name).lower()
        self._attr_unique_id = self._mac + "_" + key_formatted
        
        self._attr_name = self._name + " " + sensor_name
        self.coordinator_update()

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

    def coordinator_update(self):
        self._attr_is_on = self._device.get(self._key) == "1"

class HonBaseSensorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, appliance, key, sensor_name) -> None:
        super().__init__(coordinator)
        self._coordinator   = coordinator
        self._mac           = appliance["macAddress"]
        self._type_id       = appliance["applianceTypeId"]
        self._name          = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._brand         = appliance["brand"]
        self._model         = appliance["modelName"]
        self._fw_version    = appliance["fwVersion"]
        self._type_name     = appliance["applianceTypeName"]
        self._key           = key
        self._device        = coordinator.device


        #Generate unique ID from key
        key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        if( len(key_formatted) <= 0 ): 
            key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', sensor_name).lower()
        self._attr_unique_id = self._mac + "_" + key_formatted
        
        self._attr_name = self._name + " " + sensor_name
        self.coordinator_update()

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

    def coordinator_update(self):
        self._attr_native_value = self._device.get(self._key)


        
class HonBaseSwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, appliance, entity_description) -> None:
        super().__init__(coordinator)
        self._coordinator   = coordinator
        self._mac           = appliance["macAddress"]
        self._type_id       = appliance["applianceTypeId"]
        self._name          = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._brand         = appliance["brand"]
        self._model         = appliance["modelName"]
        self._fw_version    = appliance["fwVersion"]
        self._type_name     = appliance["applianceTypeName"]
        self._key           = entity_description.key
        self._device        = coordinator.device
        self.entity_description = entity_description

        self._attr_icon         = entity_description.icon
        self.translation_key    = entity_description.translation_key

        #Generate unique ID from key
        key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_description.key).lower()
        if( len(key_formatted) <= 0 ): 
            key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_description.name).lower()
        self._attr_unique_id = self._mac + "_" + key_formatted
        
        self._attr_name = self._name + " " + entity_description.name
        self.coordinator_update()

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

    def coordinator_update(self):
        self._attr_native_value = self._device.get(self._key)
import logging
import re
from .device import HonDevice
from .const import DOMAIN, APPLIANCE_DEFAULT_NAME
from .parameter import HonParameterFixed, HonParameterEnum, HonParameterRange, HonParameterProgram

from homeassistant.core import callback
from homeassistant.const import UnitOfTemperature, UnitOfTime, REVOLUTIONS_PER_MINUTE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import (CoordinatorEntity)
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers import translation

from homeassistant.components.number import NumberEntity, NumberEntityDescription

_LOGGER = logging.getLogger(__name__)

default_values = {
    "delayTime" : {
        "icon" : "mdi:timer-plus",
        "native_unit_of_measurement" : UnitOfTime.MINUTES
    },
    "rinseIterations" : {
        "icon" : "mdi:rotate-right",
    },
    "mainWashTime" : {
        "icon" : "mdi:clock-start",
        "native_unit_of_measurement" : UnitOfTime.MINUTES
    },
    "dryLevel" : {
        "icon" : "mdi:hair-dryer",
    },
    "tempLevel" : {
        "icon" : "mdi:thermometer",
        "native_unit_of_measurement" : UnitOfTemperature.CELSIUS
    },
    "antiCreaseTime" : {
        "icon" : "mdi:timer",
        "native_unit_of_measurement" : UnitOfTime.MINUTES
    },
    "sterilizationStatus" : {
        "icon" : "mdi:clock-start",
    },
}

async def async_setup_entry(hass, entry, async_add_entities) -> None:
    hon = hass.data[DOMAIN][entry.unique_id]
    translations = await translation.async_get_translations(hass, hass.config.language, "entity")

    appliances = []
    for appliance in hon.appliances:

        # Get or Create Coordinator
        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        #command = device.settings_command()

        for key in coordinator.device.settings:
            parameter = coordinator.device.settings[key]
            if(isinstance(parameter, HonParameterRange)
            and key.startswith("startProgram.")):

                default_value = default_values.get(parameter.key, {})
                translation_key = coordinator.device.appliance_type.lower() + '_' + parameter.key.lower()
                
                #name=translations.get(f"component.hon.entity.number.{translation_key}.name", parameter.key),

                description = NumberEntityDescription(
                    key=key,
                    name=f"{parameter.key}",
                    entity_category=EntityCategory.CONFIG,
                    #entity_category=None,
                    translation_key = translation_key,
                    icon=default_value.get("icon", None),
                    unit_of_measurement=default_value.get("unit_of_measurement", None),
                )
                appliances.extend([HonNumber(hon, coordinator, appliance, description)])


    async_add_entities(appliances)


class HonBaseNumberEntity(CoordinatorEntity, NumberEntity):
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


class HonNumber(HonBaseNumberEntity):
    _attr_has_entity_name = False  

    def __init__(self, hon, coordinator, appliance, description) -> None:
        super().__init__(coordinator, appliance, description.key, description.name)

        self._coordinator = coordinator
        self._device = coordinator.device
        self._data = self._device.settings[description.key]
        self.entity_description = description
        
        #param_display = description.key.replace("startProgram.", "").replace("tempSelZ", "Zone ")
        #self._attr_name = f"{self._name} {param_display}"
        #_LOGGER.error(self._attr_name)
        #self._attr_unique_id = f"{self._mac}-number-v59-{description.key}"

        if isinstance(self._data, HonParameterRange):
            self._attr_native_max_value = self._data.max
            self._attr_native_min_value = self._data.min
            self._attr_native_step = self._data.step

    @property
    def native_value(self) -> float | None:
        return self._device.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        self._device.settings[self.entity_description.key].value = value
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self):
        setting = self._device.settings[self.entity_description.key]
        if isinstance(setting, HonParameterRange):
            self._attr_native_max_value = setting.max
            self._attr_native_min_value = setting.min
            self._attr_native_step = setting.step
        self._attr_native_value = setting.value
        self.async_write_ha_state()
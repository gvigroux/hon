import logging
from .device import HonDevice
from .const import DOMAIN
from .parameter import HonParameterFixed, HonParameterEnum, HonParameterRange, HonParameterProgram

from homeassistant.core import callback
from homeassistant.const import UnitOfTemperature, UnitOfTime, REVOLUTIONS_PER_MINUTE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import (CoordinatorEntity)
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers import translation

from homeassistant.components.number import NumberEntity, NumberEntityDescription

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

                description = NumberEntityDescription(
                    key=key,
                    name=translations.get(f"component.hon.entity.number.{translation_key}.name", parameter.key),
                    entity_category=EntityCategory.CONFIG,
                    translation_key = translation_key,
                    icon=default_value.get("icon", None),
                    unit_of_measurement=default_value.get("unit_of_measurement", None),
                )
                appliances.extend([HonNumber(hon, coordinator, appliance, description)])


    async_add_entities(appliances)


class HonNumber(HonDevice, NumberEntity):
    def __init__(self, hon, coordinator, appliance, description) -> None:
        super().__init__(hon, coordinator, appliance)

        self._coordinator = coordinator
        self._device = coordinator.device
        self._data = self._device.settings[description.key]
        self.entity_description = description
        self._attr_unique_id = f"{self._mac}-number-{description.key}"

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
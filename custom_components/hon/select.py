import logging

from homeassistant.core import callback
from homeassistant.const import UnitOfTemperature, UnitOfTime, REVOLUTIONS_PER_MINUTE
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers import translation

from .const import DOMAIN
from .device import HonDevice
from .parameter import HonParameterFixed, HonParameterEnum, HonParameterRange, HonParameterProgram


_LOGGER = logging.getLogger(__name__)

default_values = {
    "windSpeed" : {
        "icon" : "mdi:fan",
    },
    "windDirectionHorizontal" : {
        "icon" : "mdi:swap-horizontal",
    },
    "windDirectionVertical" : {
        "icon" : "mdi:swap-vertical",
    }
}



async def async_setup_entry(hass, entry , async_add_entities) -> None:

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
            if((isinstance(parameter, HonParameterEnum) or isinstance(parameter, HonParameterProgram))
            and key.startswith("startProgram.")):

                default_value = default_values.get(parameter.key, {})
                translation_key = coordinator.device.appliance_type.lower() + '_' + parameter.key.lower()

                description = SelectEntityDescription(
                    key=key,
                    name=translations.get(f"component.hon.entity.select.{translation_key}.name", parameter.key),
                    entity_category=EntityCategory.CONFIG,
                    translation_key = translation_key,
                    icon=default_value.get("icon", None),
                    unit_of_measurement=default_value.get("unit_of_measurement", None),
                )
                appliances.extend([HonSelect(hon, coordinator, appliance, parameter, description)])


    async_add_entities(appliances)



class HonSelect(HonDevice, SelectEntity):
    def __init__(self, hon, coordinator, appliance, parameter, description ) -> None:
        super().__init__(hon, coordinator, appliance)

        self._parameter         = parameter
        self._device            = coordinator.device
        self.entity_description = description

        self._attr_unique_id = f"{self._mac}-select-{description.key}"

        if not isinstance(self._device.settings[self.entity_description.key], HonParameterFixed):
            self._attr_options: list[str] = self._device.settings[self.entity_description.key].values
        else:
            self._attr_options: list[str] = [self._device.settings[self.entity_description.key].value]


    @property
    def current_option(self) -> str | None:
        value = self._device.settings[self.entity_description.key].value
        if value is None or value not in self._attr_options:
            return None
        return value

    async def async_select_option(self, option: str) -> None:
        self._device.settings[self.entity_description.key].value = option
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self):
        setting = self._device.settings[self.entity_description.key]
        if not isinstance(self._device.settings[self.entity_description.key], HonParameterFixed):
            self._attr_options: list[str] = setting.values
        else:
            self._attr_options = [setting.value]
        self._attr_native_value = setting.value
        self.async_write_ha_state()

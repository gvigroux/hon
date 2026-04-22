import logging

from homeassistant.core import callback
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers import translation

from .const import DOMAIN
from .device import HonDevice
from .parameter import HonParameterFixed, HonParameterEnum, HonParameterProgram


_LOGGER = logging.getLogger(__name__)

default_values = {
    "windSpeed": {
        "icon": "mdi:fan",
    },
    "windDirectionHorizontal": {
        "icon": "mdi:swap-horizontal",
    },
    "windDirectionVertical": {
        "icon": "mdi:swap-vertical",
    },
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    hon = hass.data[DOMAIN][entry.unique_id]
    translations = await translation.async_get_translations(
        hass, hass.config.language, "entity"
    )

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)

        for key, parameter in coordinator.device.settings.items():
            if not isinstance(parameter, (HonParameterEnum, HonParameterProgram)):
                continue
            if key.startswith("settings.") and set(parameter.values) == {"0", "1"}:
                continue

            default_value = default_values.get(parameter.key, {})
            translation_key = (
                coordinator.device.appliance_type.lower() + "_" + parameter.key.lower()
            )

            description = SelectEntityDescription(
                key=key,
                name=translations.get(
                    f"component.hon.entity.select.{translation_key}.name", parameter.key
                ),
                entity_category=EntityCategory.CONFIG,
                translation_key=translation_key,
                icon=default_value.get("icon"),
            )
            appliances.append(HonSelect(hon, coordinator, appliance, description))

    async_add_entities(appliances)


class HonSelect(HonDevice, SelectEntity):
    def __init__(self, hon, coordinator, appliance, description) -> None:
        super().__init__(hon, coordinator, appliance)
        self._device = coordinator.device
        self.entity_description = description
        self._attr_unique_id = f"{self._mac}-select-{description.key}"
        self._refresh_options()

    def _get_setting(self):
        return self._device.get_setting(self.entity_description.key)

    def _refresh_options(self):
        setting = self._get_setting()
        if setting is None:
            self._attr_options = []
        elif isinstance(setting, HonParameterFixed):
            self._attr_options = [setting.value]
        else:
            self._attr_options = list(setting.values)

    @property
    def current_option(self) -> str | None:
        setting = self._get_setting()
        if setting is None:
            return None
        value = setting.value
        if value not in self._attr_options:
            return None
        return value

    async def async_select_option(self, option: str) -> None:
        command_name, parameter_name = self.entity_description.key.split(".", 1)
        if command_name == "settings":
            command = self._device.settings_command({parameter_name: option})
            await command.send()
            await self.coordinator.async_request_refresh()
            return

        if parameter_name == "program":
            self._device.start_command(program=option)
        else:
            self._device.start_command(parameters={parameter_name: option})
        self.coordinator.async_set_updated_data({})

    @callback
    def _handle_coordinator_update(self):
        setting = self._get_setting()
        self._refresh_options()
        self._attr_current_option = None if setting is None else setting.value
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return super().available and self._device.has_current_setting(
            self.entity_description.key
        )

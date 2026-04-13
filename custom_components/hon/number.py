from .device import HonDevice
from .const import DOMAIN
from .parameter import HonParameterRange

from homeassistant.core import callback
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers import translation
from homeassistant.components.number import NumberEntity, NumberEntityDescription


default_values = {
    "delayTime": {
        "icon": "mdi:timer-plus",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
    },
    "rinseIterations": {
        "icon": "mdi:rotate-right",
    },
    "mainWashTime": {
        "icon": "mdi:clock-start",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
    },
    "dryLevel": {
        "icon": "mdi:hair-dryer",
    },
    "tempLevel": {
        "icon": "mdi:thermometer",
        "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
    },
    "antiCreaseTime": {
        "icon": "mdi:timer",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
    },
    "sterilizationStatus": {
        "icon": "mdi:clock-start",
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
            if not isinstance(parameter, HonParameterRange):
                continue

            default_value = default_values.get(parameter.key, {})
            translation_key = (
                coordinator.device.appliance_type.lower() + "_" + parameter.key.lower()
            )

            description = NumberEntityDescription(
                key=key,
                name=translations.get(
                    f"component.hon.entity.number.{translation_key}.name", parameter.key
                ),
                entity_category=EntityCategory.CONFIG,
                translation_key=translation_key,
                icon=default_value.get("icon"),
                native_unit_of_measurement=default_value.get(
                    "native_unit_of_measurement"
                ),
            )
            appliances.append(HonNumber(hon, coordinator, appliance, description))

    async_add_entities(appliances)


class HonNumber(HonDevice, NumberEntity):
    def __init__(self, hon, coordinator, appliance, description) -> None:
        super().__init__(hon, coordinator, appliance)
        self._device = coordinator.device
        self.entity_description = description
        self._attr_unique_id = f"{self._mac}-number-{description.key}"
        self._refresh_bounds()

    def _get_setting(self):
        return self._device.get_setting(self.entity_description.key)

    def _refresh_bounds(self):
        setting = self._get_setting()
        if isinstance(setting, HonParameterRange):
            self._attr_native_max_value = setting.max
            self._attr_native_min_value = setting.min
            self._attr_native_step = setting.step

    @property
    def native_value(self) -> float | None:
        setting = self._get_setting()
        return None if setting is None else setting.value

    async def async_set_native_value(self, value: float) -> None:
        command_name, parameter_name = self.entity_description.key.split(".", 1)
        if command_name == "settings":
            command = self._device.settings_command({parameter_name: value})
            await command.send()
            await self.coordinator.async_request_refresh()
            return

        self._device.start_command(parameters={parameter_name: value})
        self.coordinator.async_set_updated_data({})

    @callback
    def _handle_coordinator_update(self):
        setting = self._get_setting()
        self._refresh_bounds()
        self._attr_native_value = None if setting is None else setting.value
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return super().available and self._device.has_current_setting(
            self.entity_description.key
        )

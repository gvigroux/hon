import logging
from dataclasses import dataclass
from typing import Any


from .const import DOMAIN
from .device import HonDevice
from .parameter import HonParameter, HonParameterFixed, HonParameterEnum, HonParameterRange, HonParameterProgram
from .base import HonBaseCoordinator, HonBaseSwitchEntity


from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntityDescription, SwitchEntity

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class HonControlSwitchEntityDescription(SwitchEntityDescription):
    turn_on_key: str = ""
    turn_off_key: str = ""


@dataclass(frozen=True)
class HonSwitchEntityDescription(SwitchEntityDescription):
    pass



async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        if (("settings" in device.commands) 
            and (device.get("silentSleepStatus", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="silentSleepStatus",
                name="Sleep Mode",
                icon="mdi:bed",
                translation_key="sleep_mode",
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description)])
            await coordinator.async_request_refresh()

        if (("settings" in device.commands) 
            and (device.get("screenDisplayStatus", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="screenDisplayStatus",
                name="Screen Display",
                icon="mdi:monitor-small",
                translation_key="screen_display_status",
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description)])
            await coordinator.async_request_refresh()


        if (("settings" in device.commands) 
            and (device.get("muteStatus", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="muteStatus",
                name="Silent Mode",
                icon="mdi:volume-off",
                translation_key="silent_mode",
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description)])
            await coordinator.async_request_refresh()


        if (("settings" in device.commands) 
            and (device.get("echoStatus", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="echoStatus",
                name="Echo",
                icon="mdi:account-voice",
                translation_key="echo_status"
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description, True)])
            await coordinator.async_request_refresh()


        if (("settings" in device.commands) 
            and (device.get("rapidMode", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="rapidMode",
                name="Rapid Mode",
                icon="mdi:car-turbocharger",
                translation_key="rapid_mode",
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description)])
            await coordinator.async_request_refresh()


        if (("settings" in device.commands) 
            and (device.get("10degreeHeatingStatus", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="10degreeHeatingStatus",
                name="10° Heating",
                icon="mdi:heat-wave",
                translation_key="10_degree_heating",
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description)])
            await coordinator.async_request_refresh()


        if (("settings" in device.commands) 
            and (device.get("ecoMode", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="ecoMode",
                name="Eco Mode",
                icon="mdi:sprout",
                translation_key="eco_mode",
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description)])
            await coordinator.async_request_refresh()


        if (("settings" in device.commands) 
            and (device.get("healthMode", "N/A") != "N/A")):

            description = HonSwitchEntityDescription(
                key="healthMode",
                name="Health Mode",
                icon="mdi:heart",
                translation_key="health_mode",
            )
            appliances.extend([HonSwitchEntity(hass, coordinator, entry, appliance, description)])
            await coordinator.async_request_refresh()


    async_add_entities(appliances)




class HonSwitchEntity(HonBaseSwitchEntity):
    entity_description: HonSwitchEntityDescription

    def __init__(self, hass, coordinator, entry, appliance, entity_description, invert = False) -> None:
        super().__init__(coordinator, appliance, entity_description)
        self.invert = invert

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if( self.invert == True ):
            return self._device.get(self.entity_description.key, "1") == "0"
        return self._device.get(self.entity_description.key, "0") == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        setting = self._device.settings[f"settings.{self.entity_description.key}"]
        if type(setting) == HonParameter:
            return
        if( self.invert == True ):
            setting.value = setting.min if isinstance(setting, HonParameterRange) else 0
        else:
            setting.value = setting.max if isinstance(setting, HonParameterRange) else 1
        await self._device.commands["settings"].send()
        self._device.set(self.entity_description.key, str(setting.value))
        self.async_write_ha_state()
        self.coordinator.async_set_updated_data({})

    async def async_turn_off(self, **kwargs: Any) -> None:
        setting = self._device.settings[f"settings.{self.entity_description.key}"]
        if type(setting) == HonParameter:
            return
        if( self.invert == True ):
            setting.value = setting.max if isinstance(setting, HonParameterRange) else 1
        else:
            setting.value = setting.min if isinstance(setting, HonParameterRange) else 0

        await self._device.commands["settings"].send()
        self._device.set(self.entity_description.key, str(setting.value))
        self.async_write_ha_state()
        self.coordinator.async_set_updated_data({})

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            _LOGGER.warning("HonSwitchEntity not available: super() is not")
            return False
        if not self._device.get("remoteCtrValid", "1") == "1":
            _LOGGER.warning("HonSwitchEntity not available: remoteCtrValid==1")
            return False
        if self._device.get("attributes.lastConnEvent.category") == "DISCONNECTED":
            _LOGGER.warning("HonSwitchEntity not available: DISCONNECTED")
            return False
        
        setting_key = f"settings.{self.entity_description.key}"
        setting = self._device.settings.get(setting_key, None)

        if setting is None:
            _LOGGER.warning("HonSwitchEntity not available: Key not found: %s", setting_key)
            return False

        #_LOGGER.warning(setting)
        #if isinstance(setting, HonParameterRange) and len(setting.values) < 2:
        #    return False
        return True

    @callback
    def _handle_coordinator_update(self, update: bool = True) -> None:
        self._attr_is_on = self.is_on
        if update:
            self.async_write_ha_state()


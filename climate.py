import logging
import asyncio
import json
import voluptuous as vol
from datetime import datetime, timedelta
from typing import Optional
from enum import IntEnum
from decimal import Decimal

from homeassistant.components.climate import (
    ClimateEntity,
)

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    DATA_RATE_MEGABITS_PER_SECOND,
)


#https://github.com/home-assistant/core/blob/a82a1bfd64708a044af7a716b5e9e057b1656f2e/homeassistant/components/climate/const.py#L70
from homeassistant.components.climate.const import (

    FAN_ON,
    FAN_OFF,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_TOP,
    FAN_MIDDLE,
    FAN_FOCUS,
    FAN_DIFFUSE,
    SWING_ON,
    SWING_OFF,
    SWING_BOTH,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    TEMP_CELSIUS,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher   import async_dispatcher_connect
from homeassistant.helpers.event        import async_track_time_interval
from homeassistant.helpers              import config_validation as cv, entity_platform
from .const import(
    DOMAIN, 
    CLIMATE_FAN_MODE,
    CLIMATE_HVAC_MODE,
    ClimateFanMode,
    ClimateHvacMode,
    ClimateSwingHorizontal,
    ClimateSwingVertical)


_LOGGER = logging.getLogger(__name__)
#SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        if appliance['applianceTypeId'] == 11:
            coordinator = await hon.async_get_coordinator(appliance)
            await coordinator.async_config_entry_first_refresh()
            appliances.append(HonClimateEntity(hass, coordinator, entry, appliance))

    async_add_entities(appliances)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "climate_set_sleep_mode",
        {
            vol.Required('sleep_mode'): cv.boolean,
        },
        "async_set_sleep_mode",
    )

    platform.async_register_entity_service(
        "climate_set_screen_display",
        {
            vol.Required('screen_display'): cv.boolean,
        },
        "async_set_screen_display",
    )

    platform.async_register_entity_service(
        "climate_set_echo_mode",
        {
            vol.Required('echo_mode'): cv.boolean,
        },
        "async_set_echo_mode",
    )

    platform.async_register_entity_service(
        "climate_set_rapid_mode",
        {
            vol.Required('rapid_mode'): cv.boolean,
        },
        "async_set_rapid_mode",
    )
    
    platform.async_register_entity_service(
        "climate_set_silent_mode",
        {
            vol.Required('silent_mode'): cv.boolean,
        },
        "async_set_silent_mode",
    )

    platform.async_register_entity_service(
        "climate_set_wind_direction_horizontal",
        {
            vol.Required('value'): cv.positive_int,
        },
        "async_set_wind_direction_horizontal",
    )
    
    platform.async_register_entity_service(
        "climate_set_wind_direction_vertical",
        {
            vol.Required('value'): cv.positive_int,
        },
        "async_set_wind_direction_vertical",
    )



# function to return key for any value
def get_key(dictionnary,val,default):
    for key, value in dictionnary.items():
        if val == value:
            return key
    return default




class HonClimateEntity(CoordinatorEntity, ClimateEntity):
    def __init__(self,hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator)
        self._coordinator   = coordinator
        self._hon           = hass.data[DOMAIN][entry.unique_id]
        self._hass          = hass
        self._brand         = appliance['brand']
        self._mac           = appliance['macAddress']
        self._name          = appliance.get('nickName', appliance.get('modelName', 'Climate'))
        self._connectivity  = appliance['connectivity']
        self._model         = appliance['modelName']
        self._series        = appliance['series']
        self._modelId       = appliance['applianceModelId']
        self._type_name     = appliance['applianceTypeName']
        self._serialNumber  = appliance['serialNumber']
        self._fwVersion     = appliance['fwVersion']
        self._unique_id     = f"{self._mac}"
        self._available     = True
        self._watcher       = None
        self._device        = coordinator.device
        
        #self._default_command = {"specialMode":"0","heatAccumulationStatus":"0","echoStatus":"0","healthMode":"0","tempSel":"21.00","humidificationStatus":"0","tempUnit":"0","humiditySel":"30","pmvStatus":"0","screenDisplayStatus":"1","windDirectionVertical":"5","lightStatus":"0","energySavingStatus":"0","lockStatus":"0","machMode":"1","windDirectionHorizontal":"0","freshAirStatus":"0","pm2p5CleaningStatus":"0","windSpeed":"5","ch2oCleaningStatus":"0","electricHeatingStatus":"0","onOffStatus":1,"energySavePeriod":"15","intelligenceStatus":"0","halfDegreeSettingStatus":"0","rapidMode":"0","operationName":"grSetDAC","silentSleepStatus":"0","voiceSignStatus":"0","voiceStatus":"0","muteStatus":"0","10degreeHeatingStatus":"0","windSensingStatus":"0","selfCleaning56Status":"0","humanSensingStatus":"0","selfCleaningStatus":"0"}

        #Not working for Farenheit
        self._attr_temperature_unit     = TEMP_CELSIUS

        self._attr_fan_modes            = [FAN_OFF, FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
        self._attr_hvac_modes           = [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.OFF, HVACMode.FAN_ONLY, HVACMode.DRY]
        self._attr_swing_modes          = [SWING_OFF, SWING_BOTH, SWING_VERTICAL, SWING_HORIZONTAL]
        self._attr_supported_features   = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.SWING_MODE
        
        self._handle_coordinator_update(False)


    async def async_set_sleep_mode(self, sleep_mode=False):
        self._sleep_mode = sleep_mode
        parameters = {"silentSleepStatus": "1" if sleep_mode else "0"}
        await self._device.settings_command(parameters).send()

    async def async_set_rapid_mode(self, rapid_mode=False):
        self._rapid_mode = rapid_mode
        parameters = {"rapidMode": "1" if rapid_mode else "0"}
        await self._device.settings_command(parameters).send()

    async def async_set_silent_mode(self, silent_mode=False):
        self._silent_mode = silent_mode
        parameters = {"muteStatus": "1" if silent_mode else "0"}
        await self._device.settings_command(parameters).send()

    async def async_set_screen_display(self, screen_display=True):
        self._screen_display = screen_display
        parameters = {"screenDisplayStatus": "1" if screen_display else "0"}
        await self._device.settings_command(parameters).send()

    async def async_set_echo_mode(self, echo_mode=False):
        self._echo_mode = echo_mode
        parameters = {"echoStatus": "0" if echo_mode else "1"}
        await self._device.settings_command(parameters).send()

    async def async_set_wind_direction_horizontal(self, value: int):
        self._wind_direction_horizontal = value
        parameters = {'windDirectionHorizontal': value}
        await self._device.settings_command(parameters).send()
        
    async def async_set_wind_direction_vertical(self, value: int):
        self._wind_direction_vertical = value
        parameters = {'windDirectionVertical': value}
        await self._device.settings_command(parameters).send()

    def start_watcher(self, timedelta=timedelta(seconds=8)):
        self._watcher = async_track_time_interval(self._hass, self.async_update_after_state_change, timedelta)
        self.async_write_ha_state()

    async def async_update_after_state_change(self, now: Optional[datetime] = None) -> None:
        self._watcher = None

    @callback
    def _handle_coordinator_update(self, update = True) -> None:

        # Watcher is running, update is not allowed because the data may not be yet accurate
        if self._watcher != None:
            return

        self._attr_target_temperature   = int(float(self._device.get('tempSel')))
        self._attr_current_temperature  = float(self._device.get('tempIndoor'))

        self.update_fan_mode(self._device.get('windSpeed'))
        self.update_hvac_mode(self._device.get('onOffStatus'),self._device.get('machMode'))
        self.update_swing_mode(self._device.get('windDirectionHorizontal'), self._device.get('windDirectionVertical'))

        self._sleep_mode    = self._device.get('silentSleepStatus') == "1"
        self._echo_mode     = self._device.get('echoStatus') == "0"
        self._screen_display= self._device.get('screenDisplayStatus') == "1"
        self._rapid_mode    = self._device.get('rapidMode') == "1"
        self._silent_mode   = self._device.get('muteStatus') == "1"
        self._wind_direction_horizontal = self._device.get('windDirectionHorizontal')
        self._wind_direction_vertical   = self._device.get('windDirectionVertical')
        
        if update: self.async_write_ha_state()

    def update_hvac_mode(self, onOff, hvac_mode):
        if onOff == "0":
            self._attr_hvac_mode = HVACMode.OFF
        else:
            self._attr_hvac_mode = get_key(CLIMATE_HVAC_MODE, hvac_mode, HVACMode.OFF)


    def update_swing_mode(self, swing_horizontal, swing_vertical):
        self._attr_swing_mode = SWING_OFF
        if swing_horizontal == ClimateSwingHorizontal.AUTO and swing_vertical == ClimateSwingVertical.AUTO :
            self._attr_swing_mode = SWING_BOTH
        elif swing_horizontal == ClimateSwingHorizontal.AUTO:
            self._attr_swing_mode = SWING_HORIZONTAL
        elif swing_vertical == ClimateSwingVertical.AUTO:
            self._attr_swing_mode = SWING_VERTICAL

    def update_fan_mode(self, wind_speed):
        self._attr_fan_mode = get_key(CLIMATE_FAN_MODE, wind_speed, FAN_MEDIUM)

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fwVersion
        }

    @property
    def state_attributes(self):
        """Return the climate state attributes."""
        attr = super().state_attributes
        attr["sleep_mode"]      = self._sleep_mode
        attr["echo_mode"]       = self._echo_mode
        attr["rapid_mode"]      = self._rapid_mode
        attr["silent_mode"]     = self._silent_mode
        attr["screen_display"]  = self._screen_display
        attr["wind_direction_horizontal"]   = self._wind_direction_horizontal
        attr["wind_direction_vertical"]     = self._wind_direction_vertical
        return attr

    #https://github.com/home-assistant/core/blob/dev/homeassistant/components/mill/climate.py
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return False
        await self._device.settings_command({'tempSel': temperature}).send()


    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        command = {}

        if hvac_mode == HVACMode.OFF:
            await self._device.stop_command().send()
        elif hvac_mode == HVACMode.COOL:
            await self._device.start_command('iot_cool').send()
        elif hvac_mode == HVACMode.HEAT:
            await self._device.start_command('iot_heat').send()
        elif hvac_mode == HVACMode.DRY:
            await self._device.start_command('iot_dry').send()
        elif hvac_mode == HVACMode.AUTO:
            await self._device.start_command('iot_auto').send()
        elif hvac_mode == HVACMode.FAN_ONLY:
            if self._attr_fan_mode == FAN_AUTO:
                self.update_fan_mode(FAN_MEDIUM)
                await self._device.start_command('iot_fan', {'windSpeed': ClimateFanMode.HON_FAN_MEDIUM} ).send()
            else:
                await self._device.start_command('iot_fan').send()
        self._attr_hvac_mode = hvac_mode
        self.start_watcher()

    async def async_set_fan_mode(self, fan_mode: str):
        self._attr_fan_mode = fan_mode
        await self._device.settings_command({'windSpeed':CLIMATE_FAN_MODE.get(fan_mode, ClimateFanMode.HON_FAN_OFF)}).send()


    async def async_set_swing_mode(self, swing_mode: str):
        
        if swing_mode == SWING_BOTH:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.AUTO, 'windDirectionVertical': ClimateSwingVertical.AUTO}

        elif swing_mode == SWING_HORIZONTAL and self._device.get('windDirectionVertical') == ClimateSwingVertical.AUTO:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.AUTO, 'windDirectionVertical': ClimateSwingVertical.MIDDLE}

        elif swing_mode == SWING_HORIZONTAL:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.AUTO}

        elif swing_mode == SWING_VERTICAL and self._device.get('windDirectionHorizontal') == ClimateSwingHorizontal.AUTO:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.MIDDLE, 'windDirectionVertical': ClimateSwingVertical.AUTO}

        elif swing_mode == SWING_VERTICAL:
            parameters = {'windDirectionVertical': ClimateSwingVertical.AUTO}

        else: #off
            parameters = {}
            if self._device.get('windDirectionHorizontal') == ClimateSwingHorizontal.AUTO:
                parameters['windDirectionHorizontal'] =  ClimateSwingHorizontal.MIDDLE
            if self._device.get('windDirectionVertical') == ClimateSwingVertical.AUTO:
                parameters['windDirectionVertical'] =  ClimateSwingVertical.MIDDLE

        self._attr_swing_mode = swing_mode
        await self._device.settings_command(parameters).send()


    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        if self._watcher != None:
            self._watcher = None


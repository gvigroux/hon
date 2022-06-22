import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from enum import IntEnum

from homeassistant.components.climate import (
    ClimateEntity,
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
from .const import(
    DOMAIN, 
    CLIMATE_FAN_MODE,
    CLIMATE_HVAC_MODE,
    ClimateFanMode,
    ClimateHvacMode,
    ClimateSwingHorizontal,
    ClimateSwingVertical)


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=15)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        if appliance['applianceTypeId'] == 11:
            appliances.append(HonClimate(hass, entry, appliance))

    async_add_entities(appliances, update_before_add=True)



# function to return key for any value
def get_key(dictionnary,val,default):
    for key, value in dictionnary.items():
        if val == value:
            return key
    return default


class HonClimate(ClimateEntity):
    def __init__(self, hass, entry, appliance) -> None:
        self._hon           = hass.data[DOMAIN][entry.unique_id]
        self._hass          = hass
        self._brand         = appliance['brand']
        self._mac           = appliance['macAddress']
        self._name          = appliance['nickName']
        self._connectivity  = appliance['connectivity']
        self._model         = appliance['modelName']
        self._series        = appliance['series']
        self._modelId       = appliance['applianceModelId']
        self._typeName      = appliance['applianceTypeName']
        self._serialNumber  = appliance['serialNumber']
        self._fwVersion     = appliance['fwVersion']
        self._unique_id     = f"{self._mac}"
        self._available     = True
        self._watcher       = None
        
        self._default_command = {"specialMode":"0","heatAccumulationStatus":"0","echoStatus":"0","healthMode":"0","tempSel":"21.00","humidificationStatus":"0","tempUnit":"0","humiditySel":"30","pmvStatus":"0","screenDisplayStatus":"1","windDirectionVertical":"5","lightStatus":"0","energySavingStatus":"0","lockStatus":"0","machMode":"1","windDirectionHorizontal":"0","freshAirStatus":"0","pm2p5CleaningStatus":"0","windSpeed":"5","ch2oCleaningStatus":"0","electricHeatingStatus":"0","onOffStatus":1,"energySavePeriod":"15","intelligenceStatus":"0","halfDegreeSettingStatus":"0","rapidMode":"0","operationName":"grSetDAC","silentSleepStatus":"0","voiceSignStatus":"0","voiceStatus":"0","muteStatus":"0","10degreeHeatingStatus":"0","windSensingStatus":"0","selfCleaning56Status":"0","humanSensingStatus":"0","selfCleaningStatus":"0"}

        #Not working for Farenheit
        self._attr_temperature_unit     = TEMP_CELSIUS
        self._attr_min_temp             = 16
        self._attr_max_temp             = 30

        self._attr_fan_modes            = [FAN_OFF, FAN_AUTO, FAN_LOW,FAN_MEDIUM,FAN_HIGH]
        self._attr_hvac_modes           = [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.OFF, HVACMode.FAN_ONLY]
        self._attr_swing_modes          = [SWING_OFF, SWING_BOTH, SWING_VERTICAL, SWING_HORIZONTAL]
        self._attr_supported_features   = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.SWING_MODE
        

    def start_watcher(self, timedelta=timedelta(seconds=1)):
        self._watcher = async_track_time_interval(self._hass, self.async_update_after_state_change, timedelta)

    async def async_update_after_state_change(self, now: Optional[datetime] = None) -> None:
        self._watcher = None

    async def async_update(self):
        # Watcher is running, update is not allowed because the data may not be yet accurate
        if self._watcher != None:
            return

        # Get state from the cloud
        json = await self._hon.async_get_state(self._mac, self._typeName)

        # No data returned by the Get State method (unauthorized...)
        if json == False:
            return
        
        # Update next command
        for parameter in json:
            if parameter in self._default_command:
                self._default_command[parameter] = json[parameter]['parNewVal']
                
            
        self._attr_target_temperature   = int(float(json['tempSel']['parNewVal']))
        self._attr_current_temperature  = float(json['tempIndoor']['parNewVal'])

        self.update_hvac_mode(self.get_int_state(json,'onOffStatus'),self.get_int_state(json,'machMode'))
        self.update_swing_mode(self.get_int_state(json,'windDirectionHorizontal'), self.get_int_state(json,'windDirectionVertical'))
        self.update_fan_mode(self.get_int_state(json,'windSpeed'))

    def get_int_state(self, json, val):
        return int(json[val]['parNewVal'])

    def get_command(self, parameters = {}):
        command = self._default_command
        command['operationName']    = 'grSetDAC'
        for key, val in parameters.items():
            if isinstance(val, IntEnum):
                command[key] = val.value
            else:
                command[key] = val
        return command

    def update_hvac_mode(self, onOff, hvac_mode):
        if onOff == 0:
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
                (DOMAIN, self._mac)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fwVersion,
        }

    #https://github.com/home-assistant/core/blob/dev/homeassistant/components/mill/climate.py
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return False
        return await self._hon.async_set(self._mac, self._typeName,self.get_command({'tempSel': temperature}))



    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.COOL:
            await self._hon.async_set(self._mac, self._typeName,self.get_command({'machMode': ClimateHvacMode.HON_HVAC_COOL}))
        elif hvac_mode == HVACMode.OFF:
            await self._hon.async_set(self._mac, self._typeName, json.loads('{"onOffStatus":"0"}'))
        elif hvac_mode == HVACMode.HEAT:
            command = self._default_command
            await self._hon.async_set(self._mac, self._typeName,self.get_command({'machMode': ClimateHvacMode.HON_HVAC_HEAT}))
        elif hvac_mode == HVACMode.AUTO:
            await self._hon.async_set(self._mac, self._typeName,self.get_command({'machMode': ClimateHvacMode.HON_HVAC_AUTO}))
        elif hvac_mode == HVACMode.FAN_ONLY:
            if self._attr_fan_mode == FAN_AUTO:
                self.update_fan_mode(FAN_MEDIUM)
                command = self.get_command({'machMode': ClimateHvacMode.HON_HVAC_FAN_ONLY, 'windSpeed': ClimateFanMode.HON_FAN_MEDIUM})
            else:
                command = self.get_command({'machMode': ClimateHvacMode.HON_HVAC_FAN_ONLY})

            await self._hon.async_set(self._mac, self._typeName, command)

        self.start_watcher(timedelta(seconds=4))
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str):
        parameters = {'windSpeed':CLIMATE_FAN_MODE.get(fan_mode, int(ClimateFanMode.HON_FAN_OFF))}
        await self._hon.async_set(self._mac, self._typeName, self.get_command(parameters))
        self.start_watcher(timedelta(seconds=4))
        self._attr_fan_mode = fan_mode
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str):
        
        if swing_mode == SWING_BOTH:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.AUTO, 'windDirectionVertical': ClimateSwingVertical.AUTO}

        elif swing_mode == SWING_HORIZONTAL and int(self._default_command['windDirectionVertical']) == ClimateSwingVertical.AUTO:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.AUTO, 'windDirectionVertical': ClimateSwingVertical.MEDIUM}

        elif swing_mode == SWING_HORIZONTAL:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.AUTO}

        elif swing_mode == SWING_VERTICAL and int(self._default_command['windDirectionHorizontal']) == ClimateSwingHorizontal.AUTO:
            parameters = {'windDirectionHorizontal': ClimateSwingHorizontal.MEDIUM, 'windDirectionVertical': ClimateSwingVertical.AUTO}

        elif swing_mode == SWING_VERTICAL:
            parameters = {'windDirectionVertical': ClimateSwingVertical.AUTO}

        else: #off
            parameters = {}
            if int(self._default_command['windDirectionHorizontal']) == ClimateSwingHorizontal.AUTO:
                parameters['windDirectionHorizontal'] =  ClimateSwingHorizontal.MEDIUM
            if int(self._default_command['windDirectionVertical']) == ClimateSwingVertical.AUTO:
                parameters['windDirectionVertical'] =  ClimateSwingVertical.MEDIUM

        await self._hon.async_set(self._mac, self._typeName, self.get_command(parameters))
        
        self.start_watcher(timedelta(seconds=4))
        self._attr_swing_mode = swing_mode
        self.async_write_ha_state()

        return


    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        if self._watcher != None:
            self._watcher = None
        

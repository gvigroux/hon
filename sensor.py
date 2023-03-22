import logging
import asyncio
from datetime import datetime, timedelta, timezone
from dateutil.tz import gettz
from typing import Optional
from enum import IntEnum
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.const import TEMP_CELSIUS, TIME_MINUTES

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

from homeassistant.core import callback

from homeassistant.helpers              import entity_platform

from .const import DOMAIN, APPLIANCE_TYPE
from .const import OVEN_PROGRAMS, DISH_WASHER_MODE, DISH_WASHER_PROGRAMS, CLIMATE_MODE
from .const import WASHING_MACHINE_MODE, WASHING_MACHINE_ERROR_CODES

from homeassistant.const import (
    UnitOfTime,
    UnitOfEnergy,
    UnitOfTemperature, 
    UnitOfMass,
    UnitOfVolume,
    REVOLUTIONS_PER_MINUTE,
    PERCENTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
)


from .base import HonBaseCoordinator, HonBaseEntity

from homeassistant.helpers.typing import StateType


from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from homeassistant.config_entries import ConfigEntry


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        
        if appliance.get("macAddress", None) == None:
            _LOGGER.warning("Appliance with no MAC")
            continue
        
        coordinator = await hon.async_get_coordinator(appliance)
        await coordinator.async_config_entry_first_refresh()

        if( "machMode" in coordinator.data ):
            appliances.extend([HonBaseMode(hass, coordinator, entry, appliance)])

        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "temp",        "Temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempEnv",     "Environment Temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempIndoor",  "Indoor Temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempOutdoor", "Outdoor Temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempSel",     "Selected Temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempSelZ1",   "Selected Temperature Zone 1")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempSelZ2",   "Selected Temperature Zone 2")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempZ1",      "Temperature Zone 1")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempZ2",      "Temperature Zone 2")

        if( "remainingTimeMM" in coordinator.data ):
            appliances.extend([HonBaseStart(hass, coordinator, entry, appliance)])
            appliances.extend([HonBaseEnd(hass, coordinator, entry, appliance)])
            appliances.extend([HonBaseRemainingTime(hass, coordinator, entry, appliance)])

        if( "humidity" in coordinator.data and int(coordinator.data["humidity"]["parNewVal"]) > 0):
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "", "")])
        if( "humidityZ1" in coordinator.data and int(coordinator.data["humidityZ1"]["parNewVal"]) > 0):
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Z1", "Zone 1")])
        if( "humidityZ2" in coordinator.data and int(coordinator.data["humidityZ2"]["parNewVal"]) > 0):
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Z2", "Zone 2")])
        if( "humidityIndoor" in coordinator.data and int(coordinator.data["humidityIndoor"]["parNewVal"]) > 0):
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Indoor", "Indoor")])
        if( "humidityOutdoor" in coordinator.data and int(coordinator.data["humidityOutdoor"]["parNewVal"]) > 0):
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Outdoor", "Outdoor")])

        if( "pm2p5ValueIndoor" in coordinator.data and float(coordinator.data["pm2p5ValueIndoor"]["parNewVal"]) > 0):
            appliances.extend([HonBaseIndoorPM2p5(hass, coordinator, entry, appliance)])
        if( "pm10ValueIndoor" in coordinator.data and float(coordinator.data["pm10ValueIndoor"]["parNewVal"]) > 0):
            appliances.extend([HonBaseIndoorPM10(hass, coordinator, entry, appliance)])

        if( "vocValueIndoor" in coordinator.data and float(coordinator.data["vocValueIndoor"]["parNewVal"]) > 0 ):
            appliances.extend([HonBaseIndoorVOC(hass, coordinator, entry, appliance)])

        if( "coLevel" in coordinator.data ):
            appliances.extend([HonBaseCOlevel(hass, coordinator, entry, appliance)])
        if( "airQuality" in coordinator.data and float(coordinator.data["airQuality"]["parNewVal"]) > 0 ):
            appliances.extend([HonBaseAIRquality(hass, coordinator, entry, appliance)])
        if( "mainFilterStatus" in coordinator.data ):
            appliances.extend([HonBaseAIRpurifyFilterLifePercentage(hass, coordinator, entry, appliance)])
        if( "preFilterStatus" in coordinator.data ):
            appliances.extend([HonBaseAIRpurifyFilterDirtPercentage(hass, coordinator, entry, appliance)])

        if( "dryLevel" in coordinator.data ):
            appliances.extend([HonBaseDryLevel(hass, coordinator, entry, appliance)])
        if( "prCode" in coordinator.data ):
            appliances.extend([HonBaseProgram(hass, coordinator, entry, appliance)])
        if( "prPhase" in coordinator.data ):
            appliances.extend([HonBaseProgramPhase(hass, coordinator, entry, appliance)])
        if( "prTime" in coordinator.data ):
            appliances.extend([HonBaseProgramDuration(hass, coordinator, entry, appliance)])

        if( "totalWaterUsed" in coordinator.data and "totalWashCycle" in coordinator.data  ):
            appliances.extend([HonBaseMeanWaterConsumption(hass, coordinator, entry, appliance)])
        if( "totalElectricityUsed" in coordinator.data and int(coordinator.data["totalElectricityUsed"]["parNewVal"]) > 0):
            appliances.extend([HonBaseTotalElectricityUsed(hass, coordinator, entry, appliance)])
        if( "totalWashCycle" in coordinator.data ):
            appliances.extend([HonBaseTotalWashCycle(hass, coordinator, entry, appliance)])
        if( "totalWaterUsed" in coordinator.data ):
            appliances.extend([HonBaseTotalWaterUsed(hass, coordinator, entry, appliance)])
        if( "actualWeight" in coordinator.data ):
            appliances.extend([HonBaseWeight(hass, coordinator, entry, appliance)])


        if( "currentWaterUsed" in coordinator.data ):
            appliances.extend([HonBaseCurrentWaterUsed(hass, coordinator, entry, appliance)])
        if( "errors" in coordinator.data ):
            appliances.extend([HonBaseError(hass, coordinator, entry, appliance)])
        if( "currentElectricityUsed" in coordinator.data ):
            appliances.extend([HonBaseCurrentElectricityUsed(hass, coordinator, entry, appliance)])

        if( "spinSpeed" in coordinator.data ):
            appliances.extend([HonBaseSpinSpeed(hass, coordinator, entry, appliance)])




        #'quickModeZ1': {'parNewVal': '0', 'lastUpdate': '2023-02-01T09:37:54Z'}, 
        #'intelligenceMode': {'parNewVal': '0', 'lastUpdate': '2023-02-04T10:40:58Z'}, 
        #'quickModeZ2': {'parNewVal': '0', 'lastUpdate': '2023-02-01T09:37:54Z'}, 
        #'holidayMode': {'parNewVal': '0', 'lastUpdate': '2023-02-01T14:41:33Z'}, 
        #'sterilizationStatus': {'parNewVal': '0', 'lastUpdate': '2023-03-19T03:49:37Z'}, 
        

        await coordinator.async_request_refresh()

    async_add_entities(appliances)



    #async def async_my_custom_service_handler(call):
    #    _LOGGER.warning(call.data)
    #    entity_id = call.data.get('entity_id')
    #    new_state = call.data.get('new_state')
    #    _LOGGER.warning(entity_id)
    #    _LOGGER.warning(new_state)
    #    async_dispatcher_connect(hass, f"state_changed.{entity_id}", lambda event: hass.async_create_task(hass.states.async_set(entity_id, new_state)))
    #hass.services.async_register(DOMAIN, 'my_custom_service', async_my_custom_service_handler)



def add_temperature_sensor(hass, coordinator, entry, appliances, appliance, parameter, name ) -> None:
    if( coordinator.data.get(parameter, None) != None ):
        appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, parameter, name)])


class HonBaseTemperature(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance, parameter, name) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._parameter = parameter
        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_{parameter}"
        self._attr_name = f"{self._name} {name}"
        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data[self._parameter]["parNewVal"]
        self.async_write_ha_state()


class HonBaseHumidity(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone = "Z1", zone_name = "Zone 1") -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._zone = zone
        self._attr_name = f"Humidity {zone_name}"
        self._attr_unique_id = f"{self._mac}_humidity_{zone}"
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:water-percent"
        
    @callback
    def _handle_coordinator_update(self):

        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["humidity" + self._zone]["parNewVal"]
        self.async_write_ha_state()	



class HonBaseMode(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id    = f"{self._mac}_machine_mode"
        self._attr_name         = f"{self._name} Mode"
        self._appliance_type_id = appliance["applianceTypeId"]
        #self._attr_icon         = "mdi:washing-machine"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return
        mode = self._coordinator.data["machMode"]["parNewVal"]
        self._attr_native_value = f"Program {mode}"

        if( self._appliance_type_id == APPLIANCE_TYPE.WASH_DRYER ):
            if mode in WASHING_MACHINE_MODE:
                self._attr_native_value = WASHING_MACHINE_MODE[mode]

        if( self._appliance_type_id == APPLIANCE_TYPE.CLIMATE ):
            if mode in CLIMATE_MODE:
                self._attr_native_value = CLIMATE_MODE[mode]

        self.async_write_ha_state()


class HonBaseRemainingTime(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id    = f"{self._mac}_remaining_time"
        self._attr_name         = f"{self._name} Remaining Time"
        self._appliance_type_id = appliance["applianceTypeId"]

        self._attr_native_unit_of_measurement = TIME_MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:progress-clock"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        delay           = 0
        remainingTime   = int(self._coordinator.data["remainingTimeMM"]["parNewVal"])
        if( "delayTime" in self._coordinator.data ):
            delay = int(self._coordinator.data["delayTime"]["parNewVal"])

        # Logic from WASHING_MACHINE implementation
        if( self._appliance_type_id == APPLIANCE_TYPE.WASHING_MACHINE ):
            if self._coordinator.data["machMode"]["parNewVal"] in ("1","6"):
                self._attr_native_value = 0
            else:
                self._attr_native_value = remainingTime

        # Logic from WASH_DRYER implementation
        elif( self._appliance_type_id == APPLIANCE_TYPE.WASH_DRYER ):
            time = delay
            if int(self._coordinator.data["machMode"]["parNewVal"]) != 7:
                time = delay + remainingTime
            self._attr_native_value = time

        else:
            self._attr_native_value = delay + remainingTime

        self._attr_native_value = time
        self.async_write_ha_state()




class HonBaseIndoorPM2p5(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_indoor_pm2p5"
        self._attr_name = f"{self._name} Indoor PM 2.5"
        self._attr_device_class = SensorDeviceClass.PM25
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._attr_icon = "mdi:blur"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["pm2p5ValueIndoor"]["parNewVal"]
        self.async_write_ha_state()


class HonBaseIndoorPM10(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_indoor_pm10"
        self._attr_name = f"{self._name} Indoor PM 10"
        self._attr_device_class = SensorDeviceClass.PM10
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._attr_icon = "mdi:blur"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["pm10ValueIndoor"]["parNewVal"]
        self.async_write_ha_state()


class HonBaseIndoorVOC(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._appliance_type_id = appliance["applianceTypeId"]
        self._attr_unique_id = f"{self._mac}_indoor_VOC"
        self._attr_name = f"{self._name} Indoor VOC"
        self._attr_icon = "mdi:chemical-weapon"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        ivoc = self._coordinator.data["vocValueIndoor"]["parNewVal"]

        if( self._appliance_type_id == APPLIANCE_TYPE.PURIFIER ):
            if ivoc in PURIFIER_VOC_VALUE:
                self._attr_native_value = PURIFIER_VOC_VALUE[ivoc]
            else:
                self._attr_native_value = f"Unknown value {ivoc}"
        else:
            self._attr_native_value = f"{ivoc}"
        self.async_write_ha_state()


class HonBaseCOlevel(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._appliance_type_id = appliance["applianceTypeId"]
        self._attr_unique_id = f"{self._mac}_co_level"
        self._attr_name = f"{self._name} CO LEVEL"
        self._attr_device_class = SensorDeviceClass.CO2
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:molecule-co2"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["coLevel"]["parNewVal"]
        self.async_write_ha_state()


class HonBaseAIRquality(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._appliance_type_id = appliance["applianceTypeId"]
        self._attr_unique_id = f"{self._mac}_air_quality"
        self._attr_name = f"{self._name} Air Quality"
        self._attr_device_class = SensorDeviceClass.AQI
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["airQuality"]["parNewVal"]
        self.async_write_ha_state()


class HonBaseAIRpurifyFilterDirtPercentage(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_air_purify_filter_dirty_percentage"
        self._attr_name = f"{self._name} FILTER DIRTY PERCENTAGE"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["preFilterStatus"]["parNewVal"]
        self.async_write_ha_state()
    

class HonBaseAIRpurifyFilterLifePercentage(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_air_purify_filter_life_percentage"
        self._attr_name = f"{self._name} FILTER LIFE PERCENTAGE"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return
        lifeperc = 100
        lifepercvaluee = self._coordinator.data["mainFilterStatus"]["parNewVal"]
        lifepercfinale = lifeperc - float(lifepercvaluee)
        self._attr_native_value = float(lifepercfinale)
        self.async_write_ha_state()
        


class HonBaseProgram(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._appliance_type_id = appliance["applianceTypeId"]
        self._attr_unique_id = f"{self._mac}_program"
        self._attr_name = f"{self._name} Program"
        self._attr_icon = "mdi:tumble-dryer"
        self._attr_device_class = "tumbledryerprogram"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        program = self._coordinator.data["prCode"]["parNewVal"]

        self._attr_native_value = f"{program}"

        if( self._appliance_type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            if program in TUMBLE_DRYER_PROGRAMS:
                self._attr_native_value = TUMBLE_DRYER_PROGRAMS[program]
            else:
                self._attr_native_value = f"Unknown program {program}"

        self.async_write_ha_state()

class HonBaseProgramPhase(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._appliance_type_id = appliance["applianceTypeId"]
        self._attr_unique_id = f"{self._mac}_program_phase"
        self._attr_name = f"{self._name} Program Phase"
        self._attr_icon = "mdi:tumble-dryer"
        self._attr_device_class = "tumbledryerprogramphase"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        programPhase = self._coordinator.data["prPhase"]["parNewVal"]
        self._attr_native_value = programPhase

        if( self._appliance_type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            if programPhase in TUMBLE_DRYER_PROGRAMS_PHASE:
                self._attr_native_value = TUMBLE_DRYER_PROGRAMS_PHASE[programPhase]
            else:
                self._attr_native_value = f"Unknown program phase {programPhase}"

        self.async_write_ha_state()

class HonBaseProgramDuration(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_duration"
        self._attr_name = f"{self._name} Program Duration"
        self._attr_native_unit_of_measurement = TIME_MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timelapse"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["prTime"]["parNewVal"]
        self.async_write_ha_state()

class HonBaseDryLevel(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._appliance_type_id = appliance["applianceTypeId"]
        self._attr_unique_id = f"{self._mac}_drylevel"
        self._attr_name = f"{self._name} Dry level"
        self._attr_icon = "mdi:hair-dryer"
        self._attr_device_class = "tumbledryerdrylevel"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        drylevel = self._coordinator.data["dryLevel"]["parNewVal"]
        self._attr_native_value = drylevel

        if( self._appliance_type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            if drylevel in TUMBLE_DRYER_DRYL:
                self._attr_native_value = TUMBLE_DRYER_DRYL[drylevel]
            else:
                self._attr_native_value = f"Unknown dry level {drylevel}"

        self.async_write_ha_state()


class HonBaseStart(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_start"
        self._attr_name = f"{self._name} Start Time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-start"
        self._on = False

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        previous = self._on
        self._on = self._coordinator.data["onOffStatus"]["parNewVal"] == "1"

        delay = 0
        if( "delayTime" in self._coordinator.data ):
            delay = int(self._coordinator.data["delayTime"]["parNewVal"])

        if delay == 0:
            if self._on is True and previous is False:
                self._attr_native_value = datetime.now(timezone.utc).replace(second=0)
            elif self._on is False:
                self._attr_native_value = None

        else:
            self._attr_native_value = datetime.now(timezone.utc).replace(
                second=0
            ) + timedelta(minutes=delay)

        self.async_write_ha_state()


class HonBaseEnd(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_end"
        self._attr_name = f"{self._name} End Time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-end"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        delay = 0
        if( "delayTime" in self._coordinator.data ):
            delay = int(self._coordinator.data["delayTime"]["parNewVal"])
        remaining = int(self._coordinator.data["remainingTimeMM"]["parNewVal"])

        if remaining == 0:
            self._attr_native_value = None
            self.async_write_ha_state()
            return

        self._attr_available = True
        self._attr_native_value = datetime.now(timezone.utc).replace(
            second=0
        ) + timedelta(minutes=delay + remaining)
        self.async_write_ha_state()


##############################################################################

class HonBaseMeanWaterConsumption(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_mean_water_consumption"
        self._attr_name = f"{self._name} Mean Water Consumption"
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water-sync"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        if int(self._coordinator.data["totalWashCycle"]["parNewVal"])-1 == 0:
            self._attr_native_value = None
        else:
            self._attr_native_value = round(float(self._coordinator.data["totalWaterUsed"]["parNewVal"])/(float(self._coordinator.data["totalWashCycle"]["parNewVal"])-1),2)
        self.async_write_ha_state()


class HonBaseTotalElectricityUsed(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_total_electricity_used"
        self._attr_name = f"{self._name} Total Electricity Used"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_icon = "mdi:connection"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = float(self._coordinator.data["totalElectricityUsed"]["parNewVal"])
        self.async_write_ha_state()


class HonBaseTotalWashCycle(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_total_wash_cycle"
        self._attr_name = f"{self._name} Total Wash Cycle"
        self._attr_icon = "mdi:counter"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = int(self._coordinator.data["totalWashCycle"]["parNewVal"])-1
        self.async_write_ha_state()


class HonBaseTotalWaterUsed(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_total_water_used"
        self._attr_name = f"{self._name} Total Water Used"
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water-pump"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = float(self._coordinator.data["totalWaterUsed"]["parNewVal"])
        self.async_write_ha_state()


class HonBaseWeight(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_weight"
        self._attr_name = f"{self._name} Estimated Weight"
        self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
        self._attr_device_class = SensorDeviceClass.WEIGHT
        self._attr_icon = "mdi:weight-kilogram"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = float(self._coordinator.data["actualWeight"]["parNewVal"])
        self.async_write_ha_state()


class HonBaseCurrentWaterUsed(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_current_water_used"
        self._attr_name = f"{self._name} Current Water Used"
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["currentWaterUsed"]["parNewVal"]
        self.async_write_ha_state()

class HonBaseError(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_error"
        self._attr_name = f"{self._name} Error"
        self._attr_icon = "mdi:math-log"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        error = self._coordinator.data["errors"]["parNewVal"]
        if error in WASHING_MACHINE_ERROR_CODES:
            self._attr_native_value = WASHING_MACHINE_ERROR_CODES[error]
        else:
            self._attr_native_value = f"Unkwon error {error}"
        self.async_write_ha_state()


class HonBaseCurrentElectricityUsed(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_current_electricity_used"
        self._attr_name = f"{self._name} Current Electricity Used"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_icon = "mdi:lightning-bolt"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return

        self._attr_native_value = self._coordinator.data["currentElectricityUsed"]["parNewVal"]
        self.async_write_ha_state()


class HonBaseSpinSpeed(SensorEntity, HonBaseEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._appliance_type_id = appliance["applianceTypeId"]
        self._attr_unique_id = f"{self._mac}_spin_Speed"
        self._attr_name = f"{self._name} Spin speed"
        self._attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
        self._attr_icon = "mdi:speedometer"

    @callback
    def _handle_coordinator_update(self):
        if self._coordinator.data is False:
            return
        
        self._attr_native_value = int(self._coordinator.data["spinSpeed"]["parNewVal"])

        if( self._appliance_type_id == APPLIANCE_TYPE.WASHING_MACHINE ):
            if self._coordinator.data["machMode"]["parNewVal"] in ("1","6"):
                self._attr_native_value = 0

        self.async_write_ha_state()
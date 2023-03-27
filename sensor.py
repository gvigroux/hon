import logging
from datetime import datetime, timedelta, timezone
from dateutil.tz import gettz
from enum import IntEnum
#from homeassistant.helpers.dispatcher import async_dispatcher_connect


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


from .const import DOMAIN, APPLIANCE_TYPE
from .const import OVEN_PROGRAMS, DISH_WASHER_MODE, DISH_WASHER_PROGRAMS, CLIMATE_MODE
from .const import WASHING_MACHINE_MODE, WASHING_MACHINE_ERROR_CODES

from homeassistant.const import (
    UnitOfTime,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature, 
    UnitOfMass,
    UnitOfVolume,
    REVOLUTIONS_PER_MINUTE,
    PERCENTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION
)

from .base import HonBaseCoordinator, HonBaseEntity, HonBaseSensorEntity

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
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempEnv",     "Environment temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempIndoor",  "Indoor temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempOutdoor", "Outdoor temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempSel",     "Selected temperature")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempSelZ1",   "Selected temperature Zone 1")
        add_temperature_sensor(hass, coordinator, entry, appliances, appliance, "tempSelZ2",   "Selected temperature Zone 2")
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
            appliances.extend([HonBaseMainFilter(hass, coordinator, entry, appliance)])
        if( "preFilterStatus" in coordinator.data ):
            appliances.extend([HonBasePreFilter(hass, coordinator, entry, appliance)])

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
        if( "totalElectricityUsed" in coordinator.data and float(coordinator.data["totalElectricityUsed"]["parNewVal"]) > 0):
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


        # Fridge other values
        if( "quickModeZ1" in coordinator.data ):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "quickModeZ1", "Quick mode Zone 1", )])
        if( "quickModeZ2" in coordinator.data ):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "quickModeZ2", "Quick mode Zone 2", )])
        if( "intelligenceMode" in coordinator.data ):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "intelligenceMode", "Intelligence mode", )])
        if( "holidayMode" in coordinator.data ):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "holidayMode", "Holiday mode", )])
        if( "sterilizationStatus" in coordinator.data ):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "sterilizationStatus", "Sterilization status", )])


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


class HonBaseMode(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "machMode", "Mode")
        #self._attr_icon         = "mdi:washing-machine"

    def coordinator_update(self):
        mode = self._coordinator.data["machMode"]["parNewVal"]
        self._attr_native_value = f"Program {mode}"

        if( self._type_id in (APPLIANCE_TYPE.WASH_DRYER, APPLIANCE_TYPE.WASHING_MACHINE)):
            if mode in WASHING_MACHINE_MODE:
                self._attr_native_value = WASHING_MACHINE_MODE[mode]

        if( self._type_id == APPLIANCE_TYPE.CLIMATE ):
            if mode in CLIMATE_MODE:
                self._attr_native_value = CLIMATE_MODE[mode]


class HonBaseTemperature(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, key, name) -> None:
        super().__init__(coordinator, appliance, key, name)

        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE


class HonBaseHumidity(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone = "Z1", zone_name = "Zone 1") -> None:
        super().__init__(coordinator, appliance, "humidity" + zone, f"Humidity {zone_name}")

        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:water-percent"
        


class HonBaseInt(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, key, name) -> None:
        super().__init__(coordinator, appliance, key, name)
        #self._attr_icon         = "mdi:washing-machine"


class HonBaseRemainingTime(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "remainingTimeMM", "Remaining Time")

        self._attr_native_unit_of_measurement = TIME_MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:progress-clock"

    def coordinator_update(self):
        delay           = 0
        remainingTime   = int(self._coordinator.data["remainingTimeMM"]["parNewVal"])
        if( "delayTime" in self._coordinator.data ):
            delay = int(self._coordinator.data["delayTime"]["parNewVal"])

        mach_mode = 0
        if( "machMode" in self._coordinator.data ):
            mach_mode = int(self._coordinator.data["machMode"]["parNewVal"])

        # Logic from WASHING_MACHINE implementation
        if( self._type_id == APPLIANCE_TYPE.WASHING_MACHINE ):
            if mach_mode in ("1","6"):
                self._attr_native_value = 0
            else:
                self._attr_native_value = remainingTime

        # Logic from WASH_DRYER implementation
        elif( self._type_id == APPLIANCE_TYPE.WASH_DRYER ):
            time = delay
            if mach_mode != 7:
                time = delay + remainingTime
            self._attr_native_value = time

        else:
            self._attr_native_value = delay + remainingTime


class HonBaseIndoorPM2p5(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "pm2p5ValueIndoor", "Indoor PM 2.5")

        self._attr_device_class = SensorDeviceClass.PM25
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._attr_icon = "mdi:blur"


class HonBaseIndoorPM10(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "pm10ValueIndoor", "Indoor PM 10")

        self._attr_device_class = SensorDeviceClass.PM10
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        self._attr_icon = "mdi:blur"


class HonBaseIndoorVOC(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "vocValueIndoor", "Indoor VO")

        self._attr_icon = "mdi:chemical-weapon"

    def coordinator_update(self):

        ivoc = self._coordinator.data["vocValueIndoor"]["parNewVal"]

        if( self._type_id == APPLIANCE_TYPE.PURIFIER ):
            if ivoc in PURIFIER_VOC_VALUE:
                self._attr_native_value = PURIFIER_VOC_VALUE[ivoc]
            else:
                self._attr_native_value = f"Unknown value {ivoc}"
        else:
            self._attr_native_value = f"{ivoc}"


class HonBaseCOlevel(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "coLevel", "CO Level")

        self._attr_device_class = SensorDeviceClass.CO2
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
        self._attr_icon = "mdi:molecule-co2"


class HonBaseAIRquality(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "airQuality", "Air Quality")

        self._attr_device_class = SensorDeviceClass.AQI
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"


class HonBasePreFilter(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "preFilterStatus", "Pre filter")

        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"

    def coordinator_update(self):
        lifeperc = 100
        lifepercvaluee = self._coordinator.data["preFilterStatus"]["parNewVal"]
        lifepercfinale = lifeperc - float(lifepercvaluee)
        self._attr_native_value = float(lifepercfinale)


class HonBaseMainFilter(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "mainFilterStatus", "Main filter")

        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"

    def coordinator_update(self):
        lifeperc = 100
        lifepercvaluee = self._coordinator.data["mainFilterStatus"]["parNewVal"]
        lifepercfinale = lifeperc - float(lifepercvaluee)
        self._attr_native_value = float(lifepercfinale)


class HonBaseProgram(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "prCode", "Program")

        self._attr_icon = "mdi:tumble-dryer"
        self._attr_device_class = "tumbledryerprogram"

    def coordinator_update(self):
        program = self._coordinator.data["prCode"]["parNewVal"]
        self._attr_native_value = f"{program}"
        if( self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            if program in TUMBLE_DRYER_PROGRAMS:
                self._attr_native_value = TUMBLE_DRYER_PROGRAMS[program]
            else:
                self._attr_native_value = f"Program {program}"


class HonBaseProgramPhase(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "prPhase", "Program phase")

        self._attr_icon = "mdi:tumble-dryer"
        self._attr_device_class = "tumbledryerprogramphase"

    def coordinator_update(self):
        programPhase = self._coordinator.data["prPhase"]["parNewVal"]
        self._attr_native_value = programPhase

        if( self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            if programPhase in TUMBLE_DRYER_PROGRAMS_PHASE:
                self._attr_native_value = TUMBLE_DRYER_PROGRAMS_PHASE[programPhase]
            else:
                self._attr_native_value = f"Phase {programPhase}"


class HonBaseProgramDuration(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "prTime", "Program duration")

        self._attr_native_unit_of_measurement = TIME_MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timelapse"


class HonBaseDryLevel(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "dryLevel", "Dry level")

        self._attr_icon = "mdi:hair-dryer"
        self._attr_device_class = "tumbledryerdrylevel" #TODO: find better value


    def coordinator_update(self):
        drylevel = self._coordinator.data["dryLevel"]["parNewVal"]
        self._attr_native_value = drylevel

        if( self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            if drylevel in TUMBLE_DRYER_DRYL:
                self._attr_native_value = TUMBLE_DRYER_DRYL[drylevel]
            else:
                self._attr_native_value = f"Dry level {drylevel}"


class HonBaseStart(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "", "Start time")

        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-start"

    def coordinator_update(self):

        if(not hasattr(self, "_on")):
            self._on = False

        previous = self._on
        if( "onOffStatus" in self._coordinator.data ):
            self._on = self._coordinator.data["onOffStatus"]["parNewVal"] == "1"
        else:
            self._on = self._coordinator.data["category"] == "CONNECTED"
            
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



class HonBaseEnd(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "", "End time")

        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-end"

    def coordinator_update(self):

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


##############################################################################

class HonBaseMeanWaterConsumption(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "", "Mean Water Consumption")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water-sync"

        #TODO: keys totalWashCycle, totalWaterUsed must be in the list

    def coordinator_update(self):
        if int(self._coordinator.data["totalWashCycle"]["parNewVal"])-1 <= 0:
            self._attr_native_value = None
        else:
            self._attr_native_value = round(float(self._coordinator.data["totalWaterUsed"]["parNewVal"])/(float(self._coordinator.data["totalWashCycle"]["parNewVal"])-1),2)


class HonBaseTotalElectricityUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalElectricityUsed", "Total electricity used")

        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:connection"

    def coordinator_update(self):
        self._attr_native_value = float(self._coordinator.data["totalElectricityUsed"]["parNewVal"])


class HonBaseTotalWashCycle(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_total_wash_cycle"
        self._attr_name = f"{self._name} Total Wash Cycle"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    def coordinator_update(self):
        self._attr_native_value = int(self._coordinator.data["totalWashCycle"]["parNewVal"])-1


class HonBaseTotalWaterUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalWaterUsed", "Total water used")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water-pump"

    def coordinator_update(self):
        self._attr_native_value = float(self._coordinator.data["totalWaterUsed"]["parNewVal"])


class HonBaseWeight(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "actualWeight", "Estimated Weight")

        self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
        self._attr_device_class = SensorDeviceClass.WEIGHT
        self._attr_icon = "mdi:weight-kilogram"

    def coordinator_update(self):
        self._attr_native_value = float(self._coordinator.data["actualWeight"]["parNewVal"])


class HonBaseCurrentWaterUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "currentWaterUsed", "Current water used")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water"

    def coordinator_update(self):
        self._attr_native_value = self._coordinator.data["currentWaterUsed"]["parNewVal"]


class HonBaseError(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "errors", "Error")

        self._attr_icon = "mdi:math-log"

    def coordinator_update(self):
        error = self._coordinator.data["errors"]["parNewVal"]
        if error in WASHING_MACHINE_ERROR_CODES:
            self._attr_native_value = WASHING_MACHINE_ERROR_CODES[error]
        else:
            self._attr_native_value = f"Error {error}"


class HonBaseCurrentElectricityUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "currentElectricityUsed", "Current electricity used")

        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:lightning-bolt"

    def coordinator_update(self):
        self._attr_native_value = self._coordinator.data["currentElectricityUsed"]["parNewVal"]


class HonBaseSpinSpeed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "spinSpeed", "Spin speed")

        self._attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:speedometer"

    def coordinator_update(self):
        self._attr_native_value = int(self._coordinator.data["spinSpeed"]["parNewVal"])

        if( self._type_id == APPLIANCE_TYPE.WASHING_MACHINE ):
            if self._coordinator.data["machMode"]["parNewVal"] in ("1","6"):
                self._attr_native_value = 0


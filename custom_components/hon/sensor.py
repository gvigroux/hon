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
from .const import WASHING_MACHINE_MODE, WASHING_MACHINE_ERROR_CODES, TUMBLE_DRYER_DRYL
from .const import TUMBLE_DRYER_MODE, TUMBLE_DRYER_MODE, TUMBLE_DRYER_PROGRAMS_PHASE, TUMBLE_DRYER_TEMPL
from .const import TUMBLE_DRYER_PROGRAMS

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

from .base import HonBaseCoordinator, HonBaseSensorEntity

from homeassistant.config_entries import ConfigEntry


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:

        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        if device.has("machMode"):
            appliances.extend([HonBaseMode(hass, coordinator, entry, appliance)])
        
        if device.has("temp"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "temp",        "Temperature")])
        if device.has("tempEnv"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempEnv",     "Environment temperature")])
        if device.has("tempIndoor"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempIndoor",  "Indoor temperature")])
        if device.has("tempOutdoor"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempOutdoor", "Outdoor temperature")])
        if device.has("tempSel"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempSel",     "Selected temperature")])
        if device.has("tempSelZ1"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempSelZ1",   "Selected temperature Zone 1")])
        if device.has("tempSelZ2"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempSelZ2",   "Selected temperature Zone 2")])
        if device.has("tempZ1"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempZ1",      "Temperature Zone 1")])
        if device.has("tempZ2"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempZ2",      "Temperature Zone 2")])

        if device.has("remainingTimeMM"):
            appliances.extend([HonBaseStart(hass, coordinator, entry, appliance)])
            appliances.extend([HonBaseEnd(hass, coordinator, entry, appliance)])
            appliances.extend([HonBaseRemainingTime(hass, coordinator, entry, appliance)])

        if device.has("humidity") and device.getInt("humidity") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "", "")])
        if device.has("humidityZ1") and device.getInt("humidityZ1") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Z1", "Zone 1")])
        if device.has("humidityZ2") and device.getInt("humidityZ2") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Z2", "Zone 2")])
        if device.has("humidityIndoor") and device.getInt("humidityIndoor") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Indoor", "Indoor")])
        if device.has("humidityOutdoor") and device.getInt("humidityOutdoor") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Outdoor", "Outdoor")])
        if device.has("humidityEnv") and device.getInt("humidityEnv") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Env", "Environment")])

        if device.has("pm2p5ValueIndoor") and device.getFloat("pm2p5ValueIndoor") > 0:
            appliances.extend([HonBaseIndoorPM2p5(hass, coordinator, entry, appliance)])
        if device.has("pm10ValueIndoor") and device.getFloat("pm10ValueIndoor") > 0:
            appliances.extend([HonBaseIndoorPM10(hass, coordinator, entry, appliance)])

        if device.has("vocValueIndoor") and device.getFloat("vocValueIndoor") > 0:
            appliances.extend([HonBaseIndoorVOC(hass, coordinator, entry, appliance)])

        if device.has("coLevel"):
            appliances.extend([HonBaseCOlevel(hass, coordinator, entry, appliance)])
        if device.has("airQuality") and device.getFloat("airQuality") > 0:
            appliances.extend([HonBaseAIRquality(hass, coordinator, entry, appliance)])
        if device.has("mainFilterStatus"):
            appliances.extend([HonBaseMainFilter(hass, coordinator, entry, appliance)])
        if device.has("preFilterStatus"):
            appliances.extend([HonBasePreFilter(hass, coordinator, entry, appliance)])

        if device.has("dryLevel"):
            appliances.extend([HonBaseDryLevel(hass, coordinator, entry, appliance)])
        if device.has("prCode"):
            appliances.extend([HonBaseProgram(hass, coordinator, entry, appliance)])
        if device.has("prPhase"):
            appliances.extend([HonBaseProgramPhase(hass, coordinator, entry, appliance)])
        if device.has("prTime"):
            appliances.extend([HonBaseProgramDuration(hass, coordinator, entry, appliance)])

        if device.has("totalWaterUsed") and device.has("totalWashCycle"):
            appliances.extend([HonBaseMeanWaterConsumption(hass, coordinator, entry, appliance)])
        if device.has("totalElectricityUsed") and device.getFloat("totalElectricityUsed") > 0:
            appliances.extend([HonBaseTotalElectricityUsed(hass, coordinator, entry, appliance)])
        if device.has("totalWashCycle"):
            appliances.extend([HonBaseTotalWashCycle(hass, coordinator, entry, appliance)])
        if device.has("totalWaterUsed"):
            appliances.extend([HonBaseTotalWaterUsed(hass, coordinator, entry, appliance)])
        if device.has("actualWeight"):
            appliances.extend([HonBaseWeight(hass, coordinator, entry, appliance)])


        if device.has("currentWaterUsed"):
            appliances.extend([HonBaseCurrentWaterUsed(hass, coordinator, entry, appliance)])
        if device.has("errors"):
            appliances.extend([HonBaseError(hass, coordinator, entry, appliance)])
        if device.has("currentElectricityUsed"):
            appliances.extend([HonBaseCurrentElectricityUsed(hass, coordinator, entry, appliance)])
        if device.has("spinSpeed"):
            appliances.extend([HonBaseSpinSpeed(hass, coordinator, entry, appliance)])


        # Fridge other values
        if device.has("quickModeZ1"):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "quickModeZ1", "Quick mode Zone 1", )])
        if device.has("quickModeZ2"):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "quickModeZ2", "Quick mode Zone 2", )])
        if device.has("intelligenceMode"):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "intelligenceMode", "Intelligence mode", )])
        if device.has("holidayMode"):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "holidayMode", "Holiday mode", )])
        if device.has("sterilizationStatus"):
            appliances.extend([HonBaseInt(hass, coordinator, entry, appliance, "sterilizationStatus", "Sterilization status", )])


        await coordinator.async_request_refresh()

    async_add_entities(appliances)





class HonBaseMode(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "machMode", "Mode")
        #self._attr_icon         = "mdi:washing-machine"

    def coordinator_update(self):
        mode = self._device.get("machMode")
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
        remainingTime   = self._device.getInt("remainingTimeMM")
        if self._device.has("delayTime"):
            delay = self._device.getInt("delayTime")

        mach_mode = 0
        if self._device.has("machMode"):
            mach_mode = self._device.getInt("machMode")

        # Logic from WASHING_MACHINE implementation
        if( self._type_id == APPLIANCE_TYPE.WASHING_MACHINE ):
            if mach_mode in (1,6):
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

        ivoc = self._device.get("vocValueIndoor")

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
        lifepercvaluee = self._device.getFloat("preFilterStatus")
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
        lifepercvaluee = self._device.getFloat("mainFilterStatus")
        lifepercfinale = lifeperc - float(lifepercvaluee)
        self._attr_native_value = float(lifepercfinale)


class HonBaseProgram(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "prCode", "Program")

        self._attr_icon = "mdi:tumble-dryer"
        self._attr_device_class = "tumbledryerprogram"

    def coordinator_update(self):
        program = self._device.get("prCode")
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
        programPhase = self._device.get("prPhase")
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
        drylevel = self._device.get("dryLevel")
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
        if self._device.has("onOffStatus"):
            self._on = self._device.get("onOffStatus") == "1"
        else:
            self._on = self._device.get("attributes.lastConnEvent.category") == "CONNECTED"

        delay = 0
        if self._device.has("delayTime"):
            delay = self._device.getInt("delayTime")

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
        if self._device.has("delayTime"):
            delay = self._device.getInt("delayTime")
        remaining = self._device.getInt("remainingTimeMM")

        if remaining == 0:
            self._attr_native_value = None
            return

        self._attr_available = True
        self._attr_native_value = datetime.now(timezone.utc).replace(second=0) + timedelta(minutes=delay + remaining)


##############################################################################

class HonBaseMeanWaterConsumption(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "", "Mean Water Consumption")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water-sync"

        #TODO: keys totalWashCycle, totalWaterUsed must be in the list

    def coordinator_update(self):
        if self._device.getInt("totalWashCycle")-1 <= 0:
            self._attr_native_value = None
        else:
            self._attr_native_value = round(self._device.getFloat("totalWaterUsed")/(self._device.getFloat("totalWashCycle")-1),2)


class HonBaseTotalElectricityUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalElectricityUsed", "Total electricity used")

        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:connection"

    def coordinator_update(self):
        self._attr_native_value =self._device.getFloat("totalElectricityUsed")


class HonBaseTotalWashCycle(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalWashCycle", "Total Wash Cycle")

        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("totalWashCycle")-1


class HonBaseTotalWaterUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalWaterUsed", "Total water used")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water-pump"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("totalWaterUsed")


class HonBaseWeight(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "actualWeight", "Estimated Weight")

        self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
        self._attr_device_class = SensorDeviceClass.WEIGHT
        self._attr_icon = "mdi:weight-kilogram"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("actualWeight")


class HonBaseCurrentWaterUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "currentWaterUsed", "Current water used")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water"

    def coordinator_update(self):
        self._attr_native_value = self._device.get("currentWaterUsed")


class HonBaseError(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "errors", "Error")

        self._attr_icon = "mdi:math-log"

    def coordinator_update(self):
        error = self._device.get("errors")
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
        self._attr_native_value = self._device.get("currentElectricityUsed")


class HonBaseSpinSpeed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "spinSpeed", "Spin speed")

        self._attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:speedometer"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("spinSpeed")

        if( self._type_id == APPLIANCE_TYPE.WASHING_MACHINE ):
            if self._device.get("machMode") in ("1","6"):
                self._attr_native_value = 0


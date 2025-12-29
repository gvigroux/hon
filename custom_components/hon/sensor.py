import logging
from datetime import datetime, timedelta, timezone

from homeassistant.core import callback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)

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

from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, APPLIANCE_TYPE
from .base import HonBaseCoordinator, HonBaseSensorEntity

divider = 1.0

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:

        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        # DEBUG: Tüm verileri logla
        _LOGGER.debug(f"=== Checking device: {device.name} ===")
        _LOGGER.debug(f"Device type: {device._type_name}")
        _LOGGER.debug(f"All attributes keys: {list(device.attributes.keys())}")
        
        if 'commandHistory' in device.attributes:
            _LOGGER.debug(f"Command History content: {device.attributes['commandHistory']}")
        
        # Program name sensörünü her cihaz için ekle (debug için)
        programName = device.getProgramName()
        _LOGGER.debug(f"getProgramName() result: {programName}")
        
        # Program name sensörünü ekle (değer None olsa bile)
        appliances.extend([HonBaseProgramName(hass, coordinator, entry, appliance)])
        _LOGGER.debug(f"Program name sensor added for {device.name}")

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
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempSelZ1",   "Selected temperature zone 1")])
        if device.has("tempSelZ2"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempSelZ2",   "Selected temperature zone 2")])
        if device.has("tempSelZ3"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempSelZ3",   "Selected temperature zone 3")])
        if device.has("tempZ1"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempZ1",      "Temperature zone 1")])
        if device.has("tempZ2"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempZ2",      "Temperature zone 2")])
        if device.has("tempZ3"):
            appliances.extend([HonBaseTemperature(hass, coordinator, entry, appliance, "tempZ3",      "Temperature zone 3")])

        if device.has("remainingTimeMM"):
            appliances.extend([HonBaseStart(hass, coordinator, entry, appliance)])
            appliances.extend([HonBaseEnd(hass, coordinator, entry, appliance)])
            appliances.extend([HonBaseRemainingTime(hass, coordinator, entry, appliance)])

        if device.has("humidity") and device.getInt("humidity") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "", "")])
        if device.has("humidityZ1") and device.getInt("humidityZ1") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Z1", "zone 1")])
        if device.has("humidityZ2") and device.getInt("humidityZ2") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Z2", "zone 2")])
        if device.has("humidityIndoor") and device.getFloat("humidityIndoor") > 0.0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Indoor", "indoor")])
        if device.has("humidityOutdoor") and device.getFloat("humidityOutdoor") > 0.0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Outdoor", "outdoor")])
        if device.has("humidityEnv") and device.getInt("humidityEnv") > 0:
            appliances.extend([HonBaseHumidity(hass, coordinator, entry, appliance, "Env", "environment")])

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


        # Parameters found for some fridges
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
    
        if( self._type_id == APPLIANCE_TYPE.CLIMATE ):
            self.translation_key    = "climate_mode"

        if( self._type_id in (APPLIANCE_TYPE.WASHING_MACHINE, APPLIANCE_TYPE.WASH_DRYER)):
            self.translation_key    = "wash_mode"
            self._attr_icon         = "mdi:washing-machine"

        if( self._type_id == APPLIANCE_TYPE.DISH_WASHER ):
            self.translation_key    = "dishwasher_mode"
    
        if( self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            self.translation_key    = "tumbledryer_mode"

        if( self._type_id == APPLIANCE_TYPE.PURIFIER ):
            self.translation_key    = "purifier_mode"
            

    def coordinator_update(self):
        mode = self._device.get("machMode")
        self._attr_native_value = f"{mode}"


class HonBaseProgramName(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "program_name", "Program name")
        
        self.translation_key = "programs_" + self._type_name.lower()
        self._attr_icon = "mdi:playlist-play"

    def coordinator_update(self):
        # Debug için tüm attributes'ı logla
        _LOGGER.debug(f"[{self._name}] All attributes: {self._device.attributes}")
        
        program_name = self._device.getProgramName()
        _LOGGER.debug(f"[{self._name}] getProgramName() returned: {program_name}")
        
        if program_name:
            self._attr_native_value = program_name
            self._attr_available = True
            _LOGGER.debug(f"[{self._name}] Program name set to: {program_name}")
        else:
            self._attr_native_value = "No program"
            self._attr_available = True
            _LOGGER.debug(f"[{self._name}] Program name set to: No program")


class HonBaseTemperature(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, key, name) -> None:
        super().__init__(coordinator, appliance, key, name)

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS


class HonBaseHumidity(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone = "Z1", zone_name = "Zone 1") -> None:
        super().__init__(coordinator, appliance, "humidity" + zone, f"Humidity {zone_name}")

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:water-percent"



class HonBaseInt(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, key, name) -> None:
        super().__init__(coordinator, appliance, key, name)
        #self._attr_icon         = "mdi:washing-machine"


class HonBaseRemainingTime(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "remainingTimeMM", "Remaining time")

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
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
        super().__init__(coordinator, appliance, "vocValueIndoor", "Indoor VOC")

        self._attr_icon         = "mdi:chemical-weapon"
        self.translation_key    = "voc" #APPLIANCE_TYPE.PURIFIER 

    def coordinator_update(self):
        voc = self._device.get("vocValueIndoor")
        self._attr_native_value = f"{voc}"


class HonBaseCOlevel(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "coLevel", "CO level")

        self._attr_device_class = SensorDeviceClass.CO2
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
        self._attr_icon = "mdi:molecule-co2"


class HonBaseAIRquality(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "airQuality", "Air quality")

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
        super().__init__(coordinator, appliance, "prCode", "Program code")

        #if( self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER):
        #    self._attr_icon         = "mdi:tumble-dryer"
        #    self.translation_key    = "tumbledryer_program"

        #if( self._type_id == APPLIANCE_TYPE.OVEN):
        #    self.translation_key    = "oven_program"

        #if( self._type_id == APPLIANCE_TYPE.DISH_WASHER):
        #    ##some programs share id but parameters (T, W, time) might be differnet. Task develop parameter adjustment
        #   self.translation_key    = "dishwasher_program"

    def coordinator_update(self):
        program = self._device.get("prCode")
        self._attr_native_value = f"{program}"


class HonBaseProgramPhase(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "prPhase", "Program phase")

        if( self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER ):
            self.translation_key    = "tumbledryer_program_phase"
            self._attr_icon         = "mdi:tumble-dryer"

        if( self._type_id in (APPLIANCE_TYPE.WASHING_MACHINE, APPLIANCE_TYPE.WASH_DRYER)):
            self.translation_key    = "wash_program_phase"
            self._attr_icon         = "mdi:washing-machine"

    def coordinator_update(self):
        programPhase = self._device.get("prPhase")
        self._attr_native_value = programPhase


class HonBaseProgramDuration(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "prTime", "Program duration")

        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timelapse"


class HonBaseDryLevel(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "dryLevel", "Dry level")

        self._attr_icon         = "mdi:hair-dryer"
        self.translation_key    = "dry_level"

    def coordinator_update(self):
        drylevel = self._device.get("dryLevel")
        self._attr_native_value = f"{drylevel}"


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

        if(not hasattr(self, "_on")):
            self._on = False
            
        if self._device.has("onOffStatus"):
            self._on = self._device.get("onOffStatus") == "1"
        else:
            self._on = self._device.get("attributes.lastConnEvent.category") == "CONNECTED"


        delay = 0
        if self._device.has("delayTime"):
            delay = self._device.getInt("delayTime")
        remaining = self._device.getInt("remainingTimeMM")

        if remaining == 0:
            self._attr_native_value = None
            return
        if self._on is False:
            self._attr_native_value = None
            return

        self._attr_available = True
        self._attr_native_value = datetime.now(timezone.utc).replace(second=0) + timedelta(minutes=delay + remaining)


##############################################################################

class HonBaseMeanWaterConsumption(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "", "Mean water consumption")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_icon = "mdi:water-sync"

        #TODO: keys totalWashCycle, totalWaterUsed must be in the list

    def coordinator_update(self):
        if self._device.getInt("totalWashCycle")-1 <= 0:
            self._attr_native_value = None
        else:
            self._attr_native_value = round((self._device.getFloat("totalWaterUsed") ) /(self._device.getFloat("totalWashCycle")-1),2)


class HonBaseTotalElectricityUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalElectricityUsed", "Total electricity used")

        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:connection"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("totalElectricityUsed")


class HonBaseTotalWashCycle(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalWashCycle", "Total wash cycle")

        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("totalWashCycle")-1


class HonBaseTotalWaterUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "totalWaterUsed", "Total water used")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water-pump"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("totalWaterUsed") / divider


class HonBaseWeight(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "actualWeight", "Estimated weight")

        self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
        self._attr_device_class = SensorDeviceClass.WEIGHT
        self._attr_icon = "mdi:weight-kilogram"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("actualWeight")


class HonBaseCurrentWaterUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "currentWaterUsed", "Current water used")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water"

    def coordinator_update(self):
        #self._attr_native_value = self._device.get("currentWaterUsed")
        self._attr_native_value = self._device.getFloat("currentWaterUsed") / divider


class HonBaseError(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "errors", "Error")

        self.translation_key    = "error"

        self._attr_icon = "mdi:math-log"
        if( self._type_id == APPLIANCE_TYPE.WASHING_MACHINE ):
            self.translation_key    = "washingmachine_error"

    def coordinator_update(self):
        error = self._device.get("errors")
        self._attr_native_value = f"{error}"


class HonBaseCurrentElectricityUsed(HonBaseSensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "currentElectricityUsed", "Current electricity used")

        #self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        #self._attr_device_class = SensorDeviceClass.POWER
        #self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:lightning-bolt"

    def coordinator_update(self):
        #self._attr_native_value = self._device.get("currentElectricityUsed")
        self._attr_native_value = self._device.getFloat("currentElectricityUsed") / divider


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

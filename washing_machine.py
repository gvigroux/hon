from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass
)

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

from homeassistant.const import (
    TIME_MINUTES,
    ENERGY_KILO_WATT_HOUR,
    TEMP_CELSIUS, 
    VOLUME_LITERS,
    UnitOfMass
)
from homeassistant.core import callback

import logging
from datetime import timedelta
from .const import DOMAIN, WASHING_MACHINE_MODE, WASHING_MACHINE_ERROR_CODES

_LOGGER = logging.getLogger(__name__)

class HonWashingMachineCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, hon, appliance):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="hOn Washing Machine",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )
        self._hon = hon
        self._mac = appliance["macAddress"]
        self._type_name = appliance["applianceTypeName"]

    async def _async_update_data(self):
        return await self._hon.async_get_state(self._mac, self._type_name)

class HonWashingMachineEntity(CoordinatorEntity):
    def __init__(self, hass, entry, coordinator, appliance) -> None:
        super().__init__(coordinator)

        self._hon = hass.data[DOMAIN][entry.unique_id]
        self._hass = hass
        self._brand = appliance["brand"]

        if "nickName" in appliance:
            self._name = appliance["nickName"]
        else:
            self._name = "Washing Machine"

        self._mac = appliance["macAddress"]
        self._connectivity = appliance["connectivity"]
        self._model = appliance["modelName"]
        self._series = appliance["series"]
        self._model_id = appliance["applianceModelId"]
        self._type_name = appliance["applianceTypeName"]
        self._serial_number = appliance["serialNumber"]
        self._fw_version = appliance["fwVersion"]

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
            "sw_version": self._fw_version,
        }
    
class HonWashingMachineCurrentElectricityUsed(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_current_electricity_used"
        self._attr_name = f"{self._name} Current Electricity Used"
        self._attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_icon = "mdi:lightning-bolt"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = json["currentElectricityUsed"]["parNewVal"]
        
        self.async_write_ha_state()

class HonWashingMachineCurrentWaterUsed(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_current_water_used"
        self._attr_name = f"{self._name} Current Water Used"
        self._attr_native_unit_of_measurement = VOLUME_LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = json["currentWaterUsed"]["parNewVal"]
        
        self.async_write_ha_state()

class HonWashingMachineError(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_error"
        self._attr_name = f"{self._name} Error"
        self._attr_icon = "mdi:math-log"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        error = json["errors"]["parNewVal"]

        if error in WASHING_MACHINE_ERROR_CODES:
            self._attr_native_value = WASHING_MACHINE_ERROR_CODES[error]
        else:
            self._attr_native_value = f"Unkwon error {error}"
        
        self.async_write_ha_state()

class HonWashingMachineLastStatus(BinarySensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_machine_last_status"
        self._attr_name = f"{self._name} Machine Last Status"
        self._attr_device_class = BinarySensorDeviceClass.POWER
        self._attr_icon = "mdi:information"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_is_on = json["category"] == "CONNECTED"
        
        self.async_write_ha_state()

class HonWashingMachineMode(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_machine_mode"
        self._attr_name = f"{self._name} Machine Mode"
        self._attr_icon = "mdi:washing-machine"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        mode = json["machMode"]["parNewVal"]

        if mode in WASHING_MACHINE_MODE:
            self._attr_native_value = WASHING_MACHINE_MODE[mode]
        else:
            self._attr_native_value = f"Unknown mode {mode}"

        self.async_write_ha_state()

class HonWashingMachineSpinSpeed(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_spin_Speed"
        self._attr_name = f"{self._name} Spin speed"
        self._attr_icon = "mdi:speedometer"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        if json["machMode"]["parNewVal"] in ("1","6"):
            self._attr_native_value = 0
        else:
            self._attr_native_value = int(json["spinSpeed"]["parNewVal"])

        self.async_write_ha_state()


class HonWashingMachineTimeRemaining(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_remaining"
        self._attr_name = f"{self._name} Time Remaining"
        self._attr_native_unit_of_measurement = TIME_MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:progress-clock"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        if json["machMode"]["parNewVal"] in ("1","6"):
            self._attr_native_value = 0
        else:
            self._attr_native_value = int(json["remainingTimeMM"]["parNewVal"]) 
            # + int( json["delayTime"])

        self.async_write_ha_state()

class HonWashingMachineTemp(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_temp"
        self._attr_name = f"{self._name} Temperature"
        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_icon = "mdi:thermometer"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        if json["machMode"]["parNewVal"] in ("1","6"):
            self._attr_native_value = 0
        else:
            self._attr_native_value = int(json["temp"]["parNewVal"])

        self.async_write_ha_state()

class HonWashingMeanWaterConsumption(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_mean_water_consumption"
        self._attr_name = f"{self._name} Mean Water Consumption"
        self._attr_native_unit_of_measurement = VOLUME_LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water-sync"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        if int(json["totalWashCycle"]["parNewVal"])-1 == 0:
            self._attr_native_value = None
        else:
            self._attr_native_value = round(float(json["totalWaterUsed"]["parNewVal"])/(float(json["totalWashCycle"]["parNewVal"])-1),2)

        self.async_write_ha_state()

class HonWashingMachineTotalElectricityUsed(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_total_electricity_used"
        self._attr_name = f"{self._name} Total Electricity Used"
        self._attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_icon = "mdi:connection"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = float(json["totalElectricityUsed"]["parNewVal"])
        
        self.async_write_ha_state()

class HonWashingMachineTotalWashCycle(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_total_wash_cycle"
        self._attr_name = f"{self._name} Total Wash Cycle"
        self._attr_icon = "mdi:counter"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = int(json["totalWashCycle"]["parNewVal"])-1
        
        self.async_write_ha_state()

class HonWashingMachineTotalWaterUsed(SensorEntity, HonWashingMachineEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(hass, entry, coordinator, appliance)

        self._coordinator = coordinator
        self._attr_unique_id = f"{self._mac}_total_water_used"
        self._attr_name = f"{self._name} Total Water Used"
        self._attr_native_unit_of_measurement = VOLUME_LITERS
        self._attr_device_class = SensorDeviceClass.VOLUME
        self._attr_icon = "mdi:water-pump"

    @callback
    def _handle_coordinator_update(self):

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = float(json["totalWaterUsed"]["parNewVal"])
        
        self.async_write_ha_state()

class HonWashingMachineWeight(SensorEntity, HonWashingMachineEntity):
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

        # Get state from the cloud
        json = self._coordinator.data

        # No data returned by the Get State method (unauthorized...)
        if json is False:
            return

        self._attr_native_value = float(json["actualWeight"]["parNewVal"])
        
        self.async_write_ha_state()

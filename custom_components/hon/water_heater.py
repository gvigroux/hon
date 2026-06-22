import logging
from datetime import timedelta
from typing import Optional
from datetime import datetime

from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, UnitOfTemperature, PRECISION_WHOLE
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)

from .const import DOMAIN, APPLIANCE_TYPE
from .parameter import HonParameterRange

_LOGGER = logging.getLogger(__name__)

# hOn operation modes for water heaters.
# The capitalized display name doubles as the HA operation_mode value (HA only
# localizes the *standard* water_heater states, so custom modes must already be
# nicely cased). Each maps to (machMode value, startProgram program key).
WH_MODES = {
    "Eco": ("1", "eco"),
    "Max": ("2", "max"),
    "BPS": ("3", "bps"),
}
MACHMODE_TO_MODE = {machmode: name for name, (machmode, _prog) in WH_MODES.items()}


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    hon = hass.data[DOMAIN][entry.unique_id]

    appliances = []
    for appliance in hon.appliances:
        if appliance["applianceTypeId"] == APPLIANCE_TYPE.WATER_HEATER:
            coordinator = await hon.async_get_coordinator(appliance)
            appliances.append(HonWaterHeaterEntity(hass, coordinator, entry, appliance))

    async_add_entities(appliances)


class HonWaterHeaterEntity(CoordinatorEntity, WaterHeaterEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator)
        self._coordinator   = coordinator
        self._hass          = hass
        self._brand         = appliance["brand"]
        self._mac           = appliance["macAddress"]
        self._name          = appliance.get("nickName", appliance.get("modelName", "Water Heater"))
        self._model         = appliance["modelName"]
        self._type_name     = appliance["applianceTypeName"]
        self._fw_version    = appliance["fwVersion"]
        self._unique_id     = f"{self._mac}_water_heater"
        self._device        = coordinator.device
        self._watcher       = None

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_operation_list = [STATE_OFF, *WH_MODES.keys()]
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.OPERATION_MODE
            | WaterHeaterEntityFeature.ON_OFF
        )

        # Read the allowed target-temperature range from the live `settings` command
        # (tempSel: 30-85 step 1 on the ES80V-F7). Falls back to sane defaults.
        self._attr_target_temperature_step = PRECISION_WHOLE
        self._attr_min_temp = 30
        self._attr_max_temp = 85
        try:
            temp_range = self._device.settings_command().parameters.get("tempSel")
            if isinstance(temp_range, HonParameterRange):
                self._attr_min_temp = temp_range.min
                self._attr_max_temp = temp_range.max
                self._attr_target_temperature_step = temp_range.step
        except Exception as e:  # pragma: no cover - defensive, keep entity alive
            _LOGGER.warning("WH: unable to read tempSel range: %s", e)

        self._update_from_device(write=False)

    # ----- helpers -------------------------------------------------------

    def _is_on(self) -> bool:
        return self._device.get("onOffStatus") == "1"

    def start_watcher(self, delay=timedelta(seconds=8)):
        """Suppress coordinator overwrites briefly so optimistic state sticks."""
        if self._watcher is not None:
            self._watcher()
        self._watcher = async_track_time_interval(
            self._hass, self._clear_watcher, delay
        )

    async def _clear_watcher(self, now: Optional[datetime] = None) -> None:
        if self._watcher is not None:
            self._watcher()
        self._watcher = None
        await self._coordinator.async_request_refresh()

    def _update_from_device(self, write=True):
        self._attr_current_temperature = float(self._device.get("temp") or 0)
        self._attr_target_temperature = float(self._device.get("tempSel") or 0)

        if not self._is_on():
            self._attr_current_operation = STATE_OFF
        else:
            self._attr_current_operation = MACHMODE_TO_MODE.get(
                str(self._device.get("machMode")), "Eco"
            )
        if write:
            self.async_write_ha_state()

    # ----- coordinator ---------------------------------------------------

    @callback
    def _handle_coordinator_update(self) -> None:
        # Watcher running: data may still reflect the pre-command state
        if self._watcher is not None:
            return
        if self._coordinator.data is False:
            return
        self._update_from_device()

    # ----- commands ------------------------------------------------------

    async def async_set_temperature(self, **kwargs) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self._device.settings_command({"tempSel": int(temperature)}).send()
        self._attr_target_temperature = int(temperature)
        self.start_watcher()
        self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode == STATE_OFF:
            await self._device.stop_command().send()
        else:
            machmode, program = WH_MODES[operation_mode]
            if self._is_on():
                # Live mode change keeps the current target temperature
                await self._device.settings_command({"machMode": machmode}).send()
            else:
                # Powered off: (re)start with the matching program
                await self._device.start_command(program).send()
        self._attr_current_operation = operation_mode
        self.start_watcher()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        mode = MACHMODE_TO_MODE.get(str(self._device.get("machMode")), "Eco")
        await self._device.start_command(WH_MODES[mode][1]).send()
        self._attr_current_operation = mode
        self.start_watcher()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._device.stop_command().send()
        self._attr_current_operation = STATE_OFF
        self.start_watcher()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._watcher is not None:
            self._watcher()
            self._watcher = None

    # ----- attributes ----------------------------------------------------

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac, self._type_name)},
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }

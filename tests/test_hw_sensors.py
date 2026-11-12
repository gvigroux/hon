"""HW (Haier HP150M8-9) sensors: water level, energy lists, mode name."""
import copy
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.hon import sensor as hon_sensor
from custom_components.hon.const import DOMAIN
from custom_components.hon.device import HonDevice
from custom_components.hon.sensor import (
    HonBaseEnergyList,
    HonBaseMode,
    HonBaseWaterLevel,
    async_setup_entry,
)

from test_hw_water_heater import APPLIANCE, COMMANDS

# Values taken from a real HP150M8-9 (fw 6.14.0) on 2026-10-30.
PARAMETERS = {
    "temp": "47",
    "tempSel": "50.0",
    "machMode": "1",
    "onOffStatus": "1",
    "errors": "00",
    "remainingWaterLevel": "12",
    "energyConsumptionYearCp": "0;0;0;0;56",
    "energyConsumptionYearEc": "0;0;0;0;0",
    "accumulatedHeatYear": "0;0;0;0;245",
    "energyConsumptionMonthCp": "0;0;0;0;0;0;0;0;0;56;0;0",
    "energyConsumptionMonthEc": "0;0;0;0;0;0;0;0;0;0;0;0",
    "accumulatedHeatMonth": "0;0;0;0;0;0;0;0;0;245;0;0",
}


async def _device(parameters=None):
    hon = MagicMock()
    hon.load_commands = AsyncMock(return_value=copy.deepcopy(COMMANDS))
    dev = HonDevice(hon, MagicMock(), APPLIANCE)
    await dev.load_commands()
    dev._attributes = {"parameters": dict(parameters or PARAMETERS)}
    return dev


def _coordinator(dev):
    coordinator = MagicMock()
    coordinator.device = dev
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def _energy(dev, key, monthly):
    return HonBaseEnergyList(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE, key, "x", monthly)


def _october():
    return patch.object(hon_sensor.dt_util, "now", return_value=datetime(2026, 10, 30, 16, 0))


@pytest.mark.asyncio
async def test_yearly_energy_is_the_last_entry():
    dev = await _device()
    assert _energy(dev, "energyConsumptionYearCp", False)._attr_native_value == 56.0
    assert _energy(dev, "accumulatedHeatYear", False)._attr_native_value == 245.0
    assert _energy(dev, "energyConsumptionYearEc", False)._attr_native_value == 0.0


@pytest.mark.asyncio
async def test_monthly_energy_is_indexed_by_calendar_month():
    dev = await _device()
    with _october():
        assert _energy(dev, "energyConsumptionMonthCp", True)._attr_native_value == 56.0
        assert _energy(dev, "accumulatedHeatMonth", True)._attr_native_value == 245.0
    with patch.object(hon_sensor.dt_util, "now", return_value=datetime(2026, 11, 1)):
        assert _energy(dev, "energyConsumptionMonthCp", True)._attr_native_value == 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["", "abc", "1;x"])
async def test_unparsable_energy_is_none_not_an_exception(bad):
    dev = await _device(dict(PARAMETERS, energyConsumptionYearCp=bad))
    assert _energy(dev, "energyConsumptionYearCp", False)._attr_native_value is None


@pytest.mark.asyncio
async def test_short_monthly_list_is_none():
    dev = await _device(dict(PARAMETERS, energyConsumptionMonthCp="1;2;3"))
    with _october():
        assert _energy(dev, "energyConsumptionMonthCp", True)._attr_native_value is None


@pytest.mark.asyncio
async def test_energy_sensor_metadata():
    dev = await _device()
    sensor = _energy(dev, "energyConsumptionYearCp", False)
    assert sensor._attr_native_unit_of_measurement == "kWh"
    assert sensor._attr_device_class == "energy"
    assert sensor._attr_state_class == "total_increasing"
    assert sensor._attr_has_entity_name is True
    assert sensor._attr_name == "x"  # just the sensor name, no appliance prefix


@pytest.mark.asyncio
async def test_water_level_and_mode_translation():
    dev = await _device()
    level = HonBaseWaterLevel(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE)
    assert level._attr_native_value == 12
    assert level._attr_has_entity_name is True
    assert level._attr_name == "Hot water level"
    mode = HonBaseMode(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE)
    assert mode.translation_key == "hw_water_heater_mode"
    assert mode._attr_native_value == "1"


@pytest.mark.asyncio
async def test_setup_creates_the_hw_sensors_only_when_the_keys_exist():
    full = await _device()
    bare = await _device({"temp": "47", "machMode": "1"})
    for dev, expected_extra in ((full, 7), (bare, 0)):
        hon = MagicMock()
        hon.appliances = [APPLIANCE]
        hon.async_get_coordinator = AsyncMock(return_value=_coordinator(dev))
        entry = MagicMock()
        entry.unique_id = "u"
        hass = MagicMock()
        hass.data = {DOMAIN: {"u": hon}}
        added = []
        await async_setup_entry(hass, entry, lambda ents: added.extend(ents))
        kinds = [type(e) for e in added]
        assert kinds.count(HonBaseEnergyList) == (6 if expected_extra else 0)
        assert kinds.count(HonBaseWaterLevel) == (1 if expected_extra else 0)


def test_mode_translation_exists_in_english():
    import json
    en = json.loads((Path(__file__).resolve().parents[1] / "custom_components/hon/translations/en.json").read_text())
    states = en["entity"]["sensor"]["hw_water_heater_mode"]["state"]
    assert states == {"1": "Auto", "2": "Eco", "3": "Electric", "4": "Vacation"}

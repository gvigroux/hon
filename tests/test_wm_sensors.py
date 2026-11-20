"""WM (Candy RP 696BWMRR/1-S) sensors: error fallback, soil/steam levels, temperature-band counters."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.hon.const import DOMAIN
from custom_components.hon.device import HonDevice
from custom_components.hon.sensor import (
    HonBaseError,
    HonBaseRawLevel,
    HonBaseTemperatureCounter,
    async_setup_entry,
)

APPLIANCE = {
    "brand": "candy",
    "applianceTypeName": "WM",
    "applianceTypeId": 1,
    "macAddress": "00-00-00-00-00-01",
    "modelName": "RP 696BWMRR/1-S",
    "applianceModelId": "1",
    "serialNumber": "S",
    "fwVersion": "1.0.0",
    "nickName": "Washing machine",
}

COMMANDS = {"applianceModel": {}, "options": {}, "dictionaryId": "x"}

# Values taken from a real Candy washer. It has no "errors" key.
PARAMETERS = {
    "error": "00",
    "dirtyLevel": "0",
    "steamLevel": "0",
    "temp0to30": "60",
    "temp40": "568",
    "temp60to90": "11",
}


async def _device(parameters=None):
    hon = MagicMock()
    hon.load_commands = AsyncMock(return_value=dict(COMMANDS))
    dev = HonDevice(hon, MagicMock(), APPLIANCE)
    await dev.load_commands()
    dev._attributes = {"parameters": dict(PARAMETERS if parameters is None else parameters)}
    return dev


def _coordinator(dev):
    coordinator = MagicMock()
    coordinator.device = dev
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def _counter(dev, key="temp40", name="x"):
    return HonBaseTemperatureCounter(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE, key, name)


async def _setup(dev):
    hon = MagicMock()
    hon.appliances = [APPLIANCE]
    hon.async_get_coordinator = AsyncMock(return_value=_coordinator(dev))
    entry = MagicMock()
    entry.unique_id = "u"
    hass = MagicMock()
    hass.data = {DOMAIN: {"u": hon}}
    added = []
    await async_setup_entry(hass, entry, lambda ents: added.extend(ents))
    return added


@pytest.mark.asyncio
async def test_error_sensor_reads_the_error_key():
    dev = await _device()
    sensor = HonBaseError(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE, "error")
    assert sensor._attr_native_value == "00"
    assert sensor.translation_key == "washingmachine_error"
    assert sensor._attr_name == "Washing machine Error"
    assert sensor._attr_unique_id == "00-00-00-00-00-01_error"


@pytest.mark.asyncio
async def test_error_sensor_default_key_is_unchanged():
    dev = await _device({"errors": "E1"})
    sensor = HonBaseError(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE)
    assert sensor._attr_native_value == "E1"
    assert sensor._attr_unique_id == "00-00-00-00-00-01_errors"


@pytest.mark.asyncio
async def test_setup_uses_error_when_errors_is_absent():
    added = await _setup(await _device())
    errors = [e for e in added if isinstance(e, HonBaseError)]
    assert len(errors) == 1
    assert errors[0]._key == "error"
    assert errors[0]._attr_native_value == "00"


@pytest.mark.asyncio
async def test_errors_wins_when_both_exist():
    added = await _setup(await _device(dict(PARAMETERS, errors="E2")))
    errors = [e for e in added if isinstance(e, HonBaseError)]
    assert len(errors) == 1
    assert errors[0]._key == "errors"
    assert errors[0]._attr_native_value == "E2"


@pytest.mark.asyncio
async def test_soil_and_steam_levels_show_the_raw_code():
    dev = await _device(dict(PARAMETERS, dirtyLevel="3"))
    soil = HonBaseRawLevel(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE, "dirtyLevel", "Soil level", "mdi:liquid-spot")
    steam = HonBaseRawLevel(MagicMock(), _coordinator(dev), MagicMock(), APPLIANCE, "steamLevel", "Steam level", "mdi:weather-fog")
    assert soil._attr_native_value == "3"
    assert steam._attr_native_value == "0"
    assert soil._attr_name == "Washing machine Soil level"
    assert soil.translation_key is None
    assert steam.translation_key is None


@pytest.mark.asyncio
async def test_counters_parse_to_ints():
    dev = await _device()
    assert _counter(dev, "temp0to30")._attr_native_value == 60
    assert _counter(dev, "temp40")._attr_native_value == 568
    assert _counter(dev, "temp60to90")._attr_native_value == 11
    assert _counter(dev)._attr_state_class == "total_increasing"
    assert _counter(dev)._attr_icon == "mdi:counter"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["", "abc"])
async def test_unparsable_counter_is_none_not_an_exception(bad):
    dev = await _device(dict(PARAMETERS, temp40=bad))
    assert _counter(dev)._attr_native_value is None


@pytest.mark.asyncio
async def test_missing_counter_is_none():
    dev = await _device({"error": "00"})
    assert _counter(dev)._attr_native_value is None


@pytest.mark.asyncio
async def test_setup_creates_the_wm_sensors_only_when_the_keys_exist():
    full = await _setup(await _device())
    bare = await _setup(await _device({"onOffStatus": "1"}))
    partial = await _setup(await _device({"steamLevel": "0", "temp40": "5"}))
    kinds = [type(e) for e in full]
    assert kinds.count(HonBaseRawLevel) == 2
    assert kinds.count(HonBaseTemperatureCounter) == 3
    assert kinds.count(HonBaseError) == 1
    assert [type(e) for e in bare].count(HonBaseRawLevel) == 0
    assert [type(e) for e in bare].count(HonBaseTemperatureCounter) == 0
    assert [type(e) for e in bare].count(HonBaseError) == 0
    assert [e._key for e in partial if isinstance(e, (HonBaseRawLevel, HonBaseTemperatureCounter))] == ["steamLevel", "temp40"]

"""Climate and water heater use the native_ temperature attributes (HA 2026.11+)."""
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.const import UnitOfTemperature
from homeassistant.helpers import deprecation
from custom_components.hon.climate import HonClimateEntity
from custom_components.hon.device import HonDevice
from custom_components.hon.water_heater import HonHwWaterHeaterEntity

from test_hw_water_heater import APPLIANCE as HW_APPLIANCE, _device as _hw_device


def _range(lo, hi, step, default):
    return {
        "typology": "range",
        "minimumValue": str(lo),
        "maximumValue": str(hi),
        "incrementValue": str(step),
        "defaultValue": str(default),
    }


AC_COMMANDS = {
    "applianceModel": {},
    "options": {},
    "dictionaryId": "x",
    "settings": {
        "parameters": {
            "tempSel": _range(16, 30, 1, 22),
            "onOffStatus": _range(0, 1, 1, 0),
            "windSpeed": {
                "typology": "enum",
                "enumValues": ["1", "2", "3", "5"],
                "defaultValue": "5",
            },
        }
    },
}

AC_APPLIANCE = {
    "brand": "haier",
    "applianceTypeName": "AC",
    "applianceTypeId": 11,
    "macAddress": "aa-bb-cc-dd-ee-ff",
    "modelName": "AS35",
    "applianceModelId": "1",
    "serialNumber": "S",
    "fwVersion": "1.0.0",
    "nickName": "Living Room",
    "connectivity": "wifi",
}


@pytest.fixture(autouse=True)
def _report_every_time():
    # Home Assistant reports a deprecated attribute once per call site.
    getattr(deprecation, "_REPORTED_DEPRECATED_ENTITY_USAGE", set()).clear()


def _ha(ent, name):
    """What Home Assistant reads: native_<name> since 2026.11, <name> before."""
    native = f"native_{name}"
    return getattr(ent, native if hasattr(type(ent), native) else name)


def _deprecations(caplog):
    return [r.getMessage() for r in caplog.records if "deprecated" in r.getMessage()]


async def _climate():
    hon = MagicMock()
    hon.load_commands = AsyncMock(return_value=AC_COMMANDS)
    hon.send_command = AsyncMock(return_value=True)
    dev = HonDevice(hon, MagicMock(), AC_APPLIANCE)
    await dev.load_commands()
    dev._attributes = {
        "parameters": {
            "tempSel": "23",
            "tempIndoor": "21.5",
            "onOffStatus": "1",
            "machMode": "1",
            "windSpeed": "5",
        }
    }
    coordinator = MagicMock()
    coordinator.device = dev
    ent = HonClimateEntity(MagicMock(), coordinator, MagicMock(), AC_APPLIANCE)
    ent.async_write_ha_state = MagicMock()
    ent.start_watcher = MagicMock()
    return ent


@pytest.mark.asyncio
async def test_climate_temperatures_without_deprecation(caplog):
    caplog.set_level(logging.WARNING)
    ent = await _climate()
    await ent.async_set_temperature(temperature=25)
    assert _ha(ent, "temperature_unit") == UnitOfTemperature.CELSIUS
    assert _ha(ent, "current_temperature") == 21.5
    assert _ha(ent, "target_temperature") == 25
    assert _deprecations(caplog) == []


@pytest.mark.asyncio
async def test_water_heater_temperatures_without_deprecation(caplog):
    caplog.set_level(logging.WARNING)
    dev, _ = await _hw_device()
    coordinator = MagicMock()
    coordinator.device = dev
    ent = HonHwWaterHeaterEntity(MagicMock(), coordinator, MagicMock(), HW_APPLIANCE)
    ent.async_write_ha_state = MagicMock()
    ent.start_watcher = MagicMock()
    await ent.async_set_temperature(temperature=55)
    assert _ha(ent, "temperature_unit") == UnitOfTemperature.CELSIUS
    assert _ha(ent, "current_temperature") == 47.0
    assert _ha(ent, "target_temperature") == 55
    assert _deprecations(caplog) == []

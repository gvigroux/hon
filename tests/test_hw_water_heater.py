"""HW (Haier HP150M8-9) water heater: type 26, setpoint via startProgram."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.components.water_heater import WaterHeaterEntityFeature
from homeassistant.exceptions import HomeAssistantError
from custom_components.hon.const import APPLIANCE_TYPE, DOMAIN
from custom_components.hon.device import HonDevice
from custom_components.hon.water_heater import (
    HonHwWaterHeaterEntity,
    HonWaterHeaterEntity,
    async_setup_entry,
)


def _range(lo, hi, step, default):
    return {
        "typology": "range",
        "minimumValue": str(lo),
        "maximumValue": str(hi),
        "incrementValue": str(step),
        "defaultValue": str(default),
    }


def _program():
    return {"parameters": {"tempSel": _range(35, 75, 1, 65)}}


COMMANDS = {
    "applianceModel": {},
    "options": {},
    "dictionaryId": "x",
    "settings": {
        "parameters": {
            "tempSel": _range(35, 75, 1, 65),
            "onOffStatus": _range(0, 1, 1, 0),
            "boostStatus": _range(0, 1, 1, 0),
        }
    },
    "startProgram": {
        "startProgram.vac": _program(),
        "startProgram.elec": _program(),
        "startProgram.eco": _program(),
        "startProgram.auto": _program(),
    },
}

APPLIANCE = {
    "brand": "haier",
    "applianceTypeName": "HW",
    "applianceTypeId": 26,
    "macAddress": "d4-e9-f4-d8-e4-dc",
    "modelName": "HP150M8-9",
    "applianceModelId": "1",
    "serialNumber": "S",
    "fwVersion": "6.14.0",
    "nickName": "Varmvatten",
}


async def _device(commands=None):
    hon = MagicMock()
    hon.load_commands = AsyncMock(return_value=commands or COMMANDS_COPY())
    hon.send_command = AsyncMock(return_value=True)
    dev = HonDevice(hon, MagicMock(), APPLIANCE)
    await dev.load_commands()
    dev._attributes = {"parameters": {"temp": "47", "tempSel": "60", "onOffStatus": "1"}}
    return dev, hon


def COMMANDS_COPY():
    import copy
    return copy.deepcopy(COMMANDS)


def _entity(dev):
    coordinator = MagicMock()
    coordinator.device = dev
    hass = MagicMock()
    ent = HonHwWaterHeaterEntity(hass, coordinator, MagicMock(), APPLIANCE)
    ent.async_write_ha_state = MagicMock()
    ent.start_watcher = MagicMock()
    return ent


def test_hw_type_id_is_26():
    assert APPLIANCE_TYPE.HW_WATER_HEATER == 26


@pytest.mark.asyncio
async def test_state_and_range_from_device():
    dev, _ = await _device()
    ent = _entity(dev)
    assert ent._attr_current_temperature == 47.0
    assert ent._attr_target_temperature == 60.0
    assert (ent._attr_min_temp, ent._attr_max_temp) == (35, 75)
    assert ent._attr_target_temperature_step == 1
    assert ent._attr_supported_features == WaterHeaterEntityFeature.TARGET_TEMPERATURE
    assert ent._attr_operation_list is None


@pytest.mark.asyncio
async def test_state_follows_on_off_status():
    dev, _ = await _device()
    ent = _entity(dev)
    assert ent._attr_current_operation == "on"
    dev._attributes["parameters"]["onOffStatus"] = "0"
    ent._update_from_device(write=False)
    assert ent._attr_current_operation == "off"


@pytest.mark.asyncio
async def test_set_temperature_sends_start_program_auto():
    dev, hon = await _device()
    ent = _entity(dev)
    await ent.async_set_temperature(temperature=55)
    hon.send_command.assert_awaited_once()
    _, name, params, _anc = hon.send_command.await_args.args
    assert name == "startProgram"
    assert params["tempSel"] == 55
    assert params["program"] == "auto"
    assert ent._attr_target_temperature == 55


@pytest.mark.asyncio
async def test_set_temperature_never_uses_settings_command():
    dev, hon = await _device()
    ent = _entity(dev)
    await ent.async_set_temperature(temperature=52)
    assert all(c.args[1] != "settings" for c in hon.send_command.await_args_list)


@pytest.mark.asyncio
async def test_set_temperature_without_value_does_nothing():
    dev, hon = await _device()
    ent = _entity(dev)
    await ent.async_set_temperature()
    hon.send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_setup_entry_picks_entity_class_by_type():
    wh_dev, _ = await _device()
    hon = MagicMock()
    other = dict(APPLIANCE, applianceTypeId=10, applianceTypeName="WH", macAddress="aa")
    hon.appliances = [APPLIANCE, other, dict(APPLIANCE, applianceTypeId=11, macAddress="bb")]
    coordinator = MagicMock()
    coordinator.device = wh_dev
    hon.async_get_coordinator = AsyncMock(return_value=coordinator)
    entry = MagicMock()
    entry.unique_id = "u"
    hass = MagicMock()
    hass.data = {DOMAIN: {"u": hon}}
    added = []
    await async_setup_entry(hass, entry, lambda ents: added.extend(ents))
    kinds = [type(e) for e in added]
    assert kinds == [HonHwWaterHeaterEntity, HonWaterHeaterEntity]


def _without_auto():
    cmds = COMMANDS_COPY()
    cmds["startProgram"] = {
        "startProgram.vac": _program(),
        "startProgram.eco": _program(),
    }
    return cmds


def _without_tempsel_program():
    cmds = COMMANDS_COPY()
    cmds["startProgram"] = {
        "startProgram.vac": {"parameters": {"onOffStatus": _range(0, 1, 1, 0)}},
        "startProgram.auto": {"parameters": {"onOffStatus": _range(0, 1, 1, 0)}},
    }
    return cmds


@pytest.mark.asyncio
async def test_never_guesses_another_program_when_no_auto():
    # vac does not heat and elec bypasses the heat pump: refuse instead.
    dev, hon = await _device(_without_auto())
    ent = _entity(dev)
    with pytest.raises(HomeAssistantError):
        await ent.async_set_temperature(temperature=55)
    hon.send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_without_tempsel_keeps_entity_but_refuses_to_set():
    dev, hon = await _device(_without_tempsel_program())
    ent = _entity(dev)  # the constructor must not raise
    # No program range to read: the range stays what the settings command gave.
    assert (ent._attr_min_temp, ent._attr_max_temp) == (35, 75)
    with pytest.raises(HomeAssistantError):
        await ent.async_set_temperature(temperature=55)
    hon.send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_send_does_not_change_displayed_target():
    dev, hon = await _device()
    ent = _entity(dev)
    hon.send_command.side_effect = RuntimeError("cloud down")
    before = ent._attr_target_temperature
    with pytest.raises(RuntimeError):
        await ent.async_set_temperature(temperature=55)
    assert ent._attr_target_temperature == before
    ent.async_write_ha_state.assert_not_called()

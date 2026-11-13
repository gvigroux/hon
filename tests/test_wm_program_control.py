"""WM (Haier HWD100-BD1499U1N washer-dryer): pause / resume / stop commands and auto-dosing binary sensors."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.exceptions import HomeAssistantError

from custom_components.hon import async_send_program_command
from custom_components.hon.binary_sensor import HonBaseGenericStatus, async_setup_entry
from custom_components.hon.const import DOMAIN
from custom_components.hon.device import HonDevice

APPLIANCE = {
    "brand": "haier",
    "applianceTypeName": "WD",
    "applianceTypeId": 2,
    "macAddress": "00-00-00-00-00-02",
    "modelName": "HWD100-BD1499U1N",
    "applianceModelId": "2",
    "serialNumber": "S",
    "fwVersion": "1.0.0",
    "nickName": "Washer dryer",
}

COMMANDS = {"applianceModel": {}, "options": {}, "dictionaryId": "x"}

# Values taken from a real Haier washer-dryer during a cotton program with auto-dosing.
PARAMETERS = {
    "onOffStatus": "1",
    "detWarn": "0",
    "softWarn": "1",
    "autoDetergentStatus": "1",
    "autoSoftenerStatus": "0",
}


async def _device(parameters=None, commands=None):
    hon = MagicMock()
    hon.load_commands = AsyncMock(return_value=dict(COMMANDS))
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    dev = HonDevice(hon, coordinator, APPLIANCE)
    await dev.load_commands()
    dev._attributes = {"parameters": dict(PARAMETERS if parameters is None else parameters)}
    dev._commands = commands if commands is not None else {}
    return dev


def _command(result=True):
    command = MagicMock()
    command.send = AsyncMock(return_value=result)
    return command


def _coordinator(dev):
    coordinator = MagicMock()
    coordinator.device = dev
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


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


def _generic(added):
    return {e._key: e for e in added if isinstance(e, HonBaseGenericStatus)}


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["pauseProgram", "resumeProgram"])
async def test_pause_and_resume_send_the_loaded_command(name):
    command = _command()
    dev = await _device(commands={name: command})
    await async_send_program_command(dev, name)
    command.send.assert_awaited_once()
    dev.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_uses_stop_command_with_current_parameters():
    command = _command()
    dev = await _device(commands={"stopProgram": MagicMock()})
    dev.stop_command = MagicMock(return_value=command)
    await async_send_program_command(dev, "stopProgram")
    dev.stop_command.assert_called_once_with()
    command.send.assert_awaited_once()
    dev.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsupported_command_lists_the_available_ones():
    dev = await _device(commands={"startProgram": _command(), "settings": _command()})
    with pytest.raises(HomeAssistantError, match=r"\[pauseProgram\].*startProgram, settings"):
        await async_send_program_command(dev, "pauseProgram")
    dev.coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejected_command_raises_and_does_not_refresh():
    dev = await _device(commands={"pauseProgram": _command(result=False)})
    with pytest.raises(HomeAssistantError, match="rejected"):
        await async_send_program_command(dev, "pauseProgram")
    dev.coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_dosing_sensors_are_created_and_read_the_parameters():
    sensors = _generic(await _setup(await _device()))
    assert sensors["detWarn"]._attr_is_on is False
    assert sensors["softWarn"]._attr_is_on is True
    assert sensors["autoDetergentStatus"]._attr_is_on is True
    assert sensors["autoSoftenerStatus"]._attr_is_on is False
    assert sensors["detWarn"]._attr_device_class == "problem"
    assert sensors["autoDetergentStatus"]._attr_device_class is None
    assert sensors["autoDetergentStatus"]._attr_name == "Washer dryer Auto detergent dosing"
    assert sensors["autoDetergentStatus"]._attr_unique_id == "00-00-00-00-00-02_auto_detergent_status"
    assert sensors["softWarn"]._attr_unique_id == "00-00-00-00-00-02_soft_warn"


@pytest.mark.asyncio
async def test_dosing_sensors_only_when_the_keys_exist():
    sensors = _generic(await _setup(await _device({"onOffStatus": "1"})))
    for key in ("detWarn", "softWarn", "autoDetergentStatus", "autoSoftenerStatus"):
        assert key not in sensors

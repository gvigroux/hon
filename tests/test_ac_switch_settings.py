"""AC (Haier split) settings switches resend the live device state, not stale cache (#301, #214)."""
import copy
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.hon.device import HonDevice
from custom_components.hon.switch import HonSwitchEntity, HonSwitchEntityDescription


def _range(lo, hi, step, default):
    return {
        "typology": "range",
        "minimumValue": str(lo),
        "maximumValue": str(hi),
        "incrementValue": str(step),
        "defaultValue": str(default),
    }


COMMANDS = {
    "applianceModel": {},
    "options": {},
    "dictionaryId": "x",
    "settings": {
        "parameters": {
            "onOffStatus": _range(0, 1, 1, 0),
            "machMode": _range(0, 6, 1, 1),
            "tempSel": _range(16, 30, 1, 24),
            "echoStatus": _range(0, 1, 1, 0),
        }
    },
}

APPLIANCE = {
    "brand": "haier",
    "applianceTypeName": "AC",
    "applianceTypeId": 1,
    "macAddress": "00-00-00-00-00-02",
    "modelName": "AS25PBPHRA-PRE",
    "applianceModelId": "1",
    "serialNumber": "S",
    "fwVersion": "1.0.0",
    "nickName": "Living Room AC",
}


async def _device():
    hon = MagicMock()
    hon.load_commands = AsyncMock(return_value=copy.deepcopy(COMMANDS))
    hon.send_command = AsyncMock(return_value=True)
    dev = HonDevice(hon, MagicMock(), APPLIANCE)
    await dev.load_commands()
    return dev, hon


def _echo_switch(dev):
    coordinator = MagicMock()
    coordinator.device = dev
    description = HonSwitchEntityDescription(key="echoStatus", name="Echo")
    ent = HonSwitchEntity(MagicMock(), coordinator, MagicMock(), APPLIANCE, description, True)
    ent.async_write_ha_state = MagicMock()
    return ent


@pytest.mark.asyncio
@pytest.mark.parametrize("turn_on, echo", [(True, "0"), (False, "1")])
async def test_echo_switch_sends_live_mode_not_stale_cache(turn_on, echo):
    dev, hon = await _device()
    # The command still holds the mode from load time; the device has since been
    # switched to heat (4) from the app and the cloud reports it.
    dev._attributes = {"parameters": {"onOffStatus": "1", "machMode": "4", "tempSel": "22",
                                      "echoStatus": "1" if turn_on else "0"}}
    ent = _echo_switch(dev)

    if turn_on:
        await ent.async_turn_on()
    else:
        await ent.async_turn_off()

    sent = hon.send_command.await_args.args[2]
    assert str(sent["machMode"]) == "4"
    assert str(sent["tempSel"]) == "22"
    assert str(sent["echoStatus"]) == echo

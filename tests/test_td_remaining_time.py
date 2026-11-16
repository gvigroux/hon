"""TD (Haier HDBI H7A2TBEX-80) remaining time: 0 in Ready and Finished, the delay plus the time left otherwise (#393)."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.hon.device import HonDevice
from custom_components.hon.sensor import HonBaseRemainingTime

APPLIANCE = {
    "brand": "haier",
    "applianceTypeName": "TD",
    "applianceTypeId": 8,
    "macAddress": "00-00-00-00-00-08",
    "modelName": "HDBI H7A2TBEX-80",
    "applianceModelId": "1",
    "serialNumber": "S",
    "fwVersion": "3.2.0",
    "nickName": "Tumble Dryer",
}

COMMANDS = {"applianceModel": {}, "options": {}, "dictionaryId": "x"}


async def _device(parameters, appliance=APPLIANCE):
    hon = MagicMock()
    hon.load_commands = AsyncMock(return_value=dict(COMMANDS))
    dev = HonDevice(hon, MagicMock(), appliance)
    await dev.load_commands()
    dev._attributes = {"parameters": dict(parameters)}
    return dev


def _coordinator(dev):
    coordinator = MagicMock()
    coordinator.device = dev
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def _remaining(parameters, appliance=APPLIANCE):
    dev = await _device(parameters, appliance)
    return HonBaseRemainingTime(MagicMock(), _coordinator(dev), MagicMock(), appliance)._attr_native_value


# In Ready a real dryer reports the selected program's full length (144 min here) and keeps it after switching
# itself off. Finished has no cycle to time either, whatever remainingTimeMM holds.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode, remaining, delay, expected",
    [
        ("1", "144", "0", 0),  # Ready, after the door is opened at the end of a cycle
        ("7", "0", "0", 0),  # Finished
        ("7", "2", "0", 0),  # Finished with minutes left in remainingTimeMM
        ("2", "130", "0", 130),  # Running
        ("3", "153", "0", 153),  # Paused, door opened mid-cycle
        ("5", "30", "60", 90),  # Delayed start: the delay is added, as before
    ],
)
async def test_tumble_dryer_remaining_time(mode, remaining, delay, expected):
    assert await _remaining({"machMode": mode, "remainingTimeMM": remaining, "delayTime": delay}) == expected


@pytest.mark.asyncio
async def test_tumble_dryer_without_a_mode_keeps_the_delay_plus_the_time_left():
    assert await _remaining({"remainingTimeMM": "45", "delayTime": "10"}) == 55


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "type_name, type_id, mode, expected",
    [
        ("WM", 1, "1", 0),  # washing machine in Ready, as before
        ("WM", 1, "7", 144),  # washing machine in Finished, as before
        ("WD", 2, "7", 0),  # wash dryer in Finished: the delay only, as before
        ("WD", 2, "1", 144),  # wash dryer in Ready, as before
    ],
)
async def test_other_appliances_are_unchanged(type_name, type_id, mode, expected):
    appliance = dict(APPLIANCE, applianceTypeName=type_name, applianceTypeId=type_id)
    parameters = {"machMode": mode, "remainingTimeMM": "144", "delayTime": "0"}
    assert await _remaining(parameters, appliance) == expected

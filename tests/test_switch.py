"""Switch setup: each mode switch is created from its own reported key."""
import copy
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.hon.const import DOMAIN
from custom_components.hon.device import HonDevice
from custom_components.hon.switch import async_setup_entry

APPLIANCE = {
    "brand": "haier",
    "applianceTypeName": "AC",
    "applianceTypeId": 11,
    "macAddress": "00-00-00-00-00-02",
    "modelName": "AC",
    "applianceModelId": "1",
    "serialNumber": "S",
    "fwVersion": "1.0.0",
    "nickName": "Air conditioner",
}

COMMANDS = {"applianceModel": {}, "options": {}, "dictionaryId": "x", "settings": {"parameters": {}}}


async def _setup_keys(parameters):
    hon_api = MagicMock()
    hon_api.load_commands = AsyncMock(return_value=copy.deepcopy(COMMANDS))
    dev = HonDevice(hon_api, MagicMock(), APPLIANCE)
    await dev.load_commands()
    dev._attributes = {"parameters": dict(parameters)}
    coordinator = MagicMock()
    coordinator.device = dev
    coordinator.async_request_refresh = AsyncMock()
    hon = MagicMock()
    hon.appliances = [APPLIANCE]
    hon.async_get_coordinator = AsyncMock(return_value=coordinator)
    entry = MagicMock()
    entry.unique_id = "u"
    hass = MagicMock()
    hass.data = {DOMAIN: {"u": hon}}
    added = []
    await async_setup_entry(hass, entry, lambda ents: added.extend(ents))
    return sorted(e.entity_description.key for e in added)


@pytest.mark.asyncio
async def test_turbo_mode_switch_follows_turbo_mode_key():
    assert await _setup_keys({"ecoMode": "0"}) == ["ecoMode"]
    assert await _setup_keys({"turboMode": "0"}) == ["turboMode"]

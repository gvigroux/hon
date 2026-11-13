"""send_command: cloud replies without a payload are treated as a rejected command."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.hon.hon import HonConnection


@pytest.mark.asyncio
async def test_send_command_without_payload_returns_false():
    with patch("custom_components.hon.hon.aiohttp.ClientSession"):
        hon = HonConnection(MagicMock(), MagicMock())
    hon._ensure_session = AsyncMock()
    resp = MagicMock()
    resp.json = AsyncMock(return_value={"errorMessage": "Bad Request"})
    hon._session.post.return_value.__aenter__.return_value = resp
    device = MagicMock(mac_address="00-00-00-00-00-01", appliance_type="OV")

    assert await hon.send_command(device, "startProgram", {"program": "x"}, {}) is False

import asyncio
import logging
import voluptuous as vol
import aiohttp
import asyncio
import secrets
import hashlib
import base64
import json
import re
import ast
import time
import urllib.parse
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr


from .const import (
    DOMAIN,
    CONF_ID_TOKEN,
    CONF_COGNITO_TOKEN,
    CONF_REFRESH_TOKEN,
    API_URL,
    APP_VERSION,
    OS_VERSION,
    OS,
    DEVICE_MODEL,
)

# CIAM access tokens expire after ~15 minutes, so refresh well before that.
SESSION_TIMEOUT     = 600 # seconds

from .base import HonBaseCoordinator



class HonConnection:
    def __init__(self, hass, entry, email = None, password = None) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator_dict  = {}
        self._mobile_id = secrets.token_hex(8)

        # Only used during registration (Login/password check)
        if( email != None ) and ( password != None ):
            self._email = email
            self._password = password
        else:
            self._email = entry.data[CONF_EMAIL]
            self._password = entry.data[CONF_PASSWORD]
            self._id_token = entry.data.get(CONF_ID_TOKEN, "")
            self._refresh_token = entry.data.get(CONF_REFRESH_TOKEN, "")
            self._cognitoToken = entry.data.get(CONF_COGNITO_TOKEN, "")

        self._start_time    = time.time()

        self._header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        self._session = aiohttp.ClientSession(headers=self._header, connector=aiohttp.TCPConnector(ssl=False))
        self._appliances = []

    async def async_close(self):
        await self._session.close()

    @property
    def appliances(self):
        return self._appliances

    async def async_get_existing_coordinator(self, mac):
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac]
        return None

    async def async_get_coordinator(self, appliance):
        mac = appliance.get("macAddress", "")
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac]
        coordinator = HonBaseCoordinator(self._hass, self, appliance)
        self._coordinator_dict[mac] = coordinator
        return coordinator


    async def _ensure_session(self):
        """Re-authenticate when the CIAM tokens are close to expiring (~15 min TTL)."""
        if time.time() - self._start_time > SESSION_TIMEOUT:
            await self.async_authorize()

    async def async_authorize(self):
        """Authenticate against the hOn CIAM endpoint and load the appliances.

        Replaces the legacy Salesforce Aura / OAuth2 login that Haier retired in
        2026-06: the app now logs in through /ciam/authorize + /ciam/token (PKCE)
        and reads appliances from /unified-api/v1/view/appliance-list. The old
        /commands/v1/appliance endpoint now returns an empty list.
        """
        # PKCE (S256) verifier + challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        # 1) Submit credentials, receive a one-time session id
        params = {
            "username": self._email,
            "password": self._password,
            "code_challenge": code_challenge,
        }
        async with self._session.get(f"{API_URL}/ciam/authorize", params=params) as resp:
            if resp.status != 200:
                _LOGGER.error("Unable to connect to the CIAM authorize service: " + str(resp.status))
                return False
            session_id = (await resp.json()).get("session_id")
            if not session_id:
                _LOGGER.error("Unable to get [session_id] - check your email/password")
                return False

        # 2) Exchange the session id (+ PKCE verifier) for the tokens
        async with self._session.post(
            f"{API_URL}/ciam/token",
            json={"session_id": session_id, "code_verifier": code_verifier},
        ) as resp:
            try:
                tokens = (await resp.json())["tokens"]
                self._cognitoToken = tokens["cognito_token"]
                self._id_token = tokens["id_token"]
                self._refresh_token = tokens.get("refresh_token", "")
            except (KeyError, TypeError):
                _LOGGER.error("Unable to get tokens from /ciam/token. Response: " + await resp.text())
                return False

        # 3) Load the appliance list from the unified-api view
        url = f"{API_URL}/unified-api/v1/view/appliance-list"
        async with self._session.post(url, headers=self._headers, json={"deviceId": "homeassistant"}) as resp:
            try:
                json_data = await resp.json()
                self._appliances = json_data["modules"]["applianceList"]["payload"]["appliances"]
            except (KeyError, TypeError):
                _LOGGER.error("hOn Invalid Data [" + (await resp.text())[:500] + "] after POST [" + url + "]")
                return False

            _LOGGER.debug(f"All appliances: {self._appliances}")

            # Keep only appliances that expose a MAC address and a type id
            self._appliances = [
                appliance for appliance in self._appliances
                if "macAddress" in appliance and "applianceTypeId" in appliance
            ]

        self._start_time = time.time()
        return True


    async def load_commands(self, appliance):
        params = {
            "applianceType": appliance["applianceTypeId"],
            "code": appliance["code"],
            "applianceModelId": appliance["applianceModelId"],
            "firmwareId": appliance["eepromId"],
            "macAddress": appliance["macAddress"],
            "fwVersion": appliance["fwVersion"],
            "os": OS,
            "appVersion": APP_VERSION,
            "series": appliance["series"],
        }
        url = f"{API_URL}/commands/v1/retrieve"
        async with self._session.get(url, params=params, headers=self._headers) as resp:
            result = (await resp.json()).get("payload", {})
            if not result or result.pop("resultCode") != "0":
                return {}
            _LOGGER.debug(f"Commands: {result}")
            return result

    async def async_get_context(self, device):

        # Refresh the CIAM session before it expires
        await self._ensure_session()

        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type,
            "category": "CYCLE"
        }
        url = f"{API_URL}/commands/v1/context"
        async with self._session.get(url, params=params, headers=self._headers) as response:
            data = await response.json()
            _LOGGER.debug(f"Context for mac[{device.mac_address}] type [{device.appliance_type}] {data}")
            return data.get("payload", {})

    async def load_statistics(self, device):
        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type
        }
        url = f"{API_URL}/commands/v1/statistics"
        async with self._session.get(url, params=params, headers=self._headers) as response:
            data = await response.json()
            _LOGGER.debug(f"Statistic for mac[{device.mac_address}] type [{device.appliance_type}] {data}")
            return data.get("payload", {})

    @property
    def _headers(self):
        return {
            "Content-Type": "application/json",
            "cognito-token": self._cognitoToken,
            "id-token": self._id_token,
        }

    async def async_set(self, mac, typeName, parameters):

        await self._ensure_session()

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        command = json.loads("{}")
        command["macAddress"] = mac
        command["commandName"] = "startProgram"
        command["applianceOptions"] = json.loads("{}")
        command["programName"] = "PROGRAMS." + typeName + ".HOME_ASSISTANT"
        command["ancillaryParameters"] = json.loads(
            '{"programFamily":"[standard]", "remoteActionable": "1", "remoteVisible": "1"}'
        )
        command["applianceType"] = typeName
        command["attributes"] = json.loads(
            '{"prStr":"HOME_ASSISTANT", "channel":"googleHome", "origin": "conversationalVoice"}'
        )
        if typeName == "WM":
            command["attributes"] = json.loads(
            '{"prStr":"HOME_ASSISTANT", "channel":"googleHome", "origin": "conversationalVoice", "energyLabel": "0"}'
        )
        command["device"] = json.loads(
            '{"mobileId":"xxxxxxxxxxxxxxxxxxx", "mobileOs": "android", "osVersion": "31", "appVersion": "1.53.4", "deviceModel": "lito"}'
        )
        command["parameters"] = parameters
        command["timestamp"] = timestamp
        command["transactionId"] = mac + "_" + command["timestamp"]
        _LOGGER.debug((f"Command sent (async_set): {command}"))

        async with self._session.post(f"{API_URL}/commands/v1/send",headers=self._headers,json=command,) as resp:
            try:
                data = await resp.json()
                _LOGGER.debug((f"Command result (async_set): {data}"))
            except json.JSONDecodeError:
                _LOGGER.error("hOn Invalid Data ["+ str(resp.text()) + "] after sending command ["+ str(command)+ "]")
                return False
            if data["payload"]["resultCode"] == "0":
                return True
            _LOGGER.error("hOn command has been rejected. Error message ["+ str(data) + "] sent command ["+ str(command)+ "]")
        return False


    async def send_command(self, device, command, parameters, ancillary_parameters):

        await self._ensure_session()

        now = datetime.utcnow().isoformat()
        command = {
            "macAddress": device.mac_address,
            "timestamp": f"{now[:-3]}Z",
            "commandName": command,
            "transactionId": f"{device.mac_address}_{now[:-3]}Z",
            "applianceOptions": device.commands_options,
            "device": {
                "mobileId": self._mobile_id,
                "mobileOs": OS,
                "osVersion": OS_VERSION,
                "appVersion": APP_VERSION,
                "deviceModel": DEVICE_MODEL
            },
            "attributes": {
                "channel": "mobileApp",
                "origin": "standardProgram",
                "energyLabel": "0"
            },
            "ancillaryParameters": ancillary_parameters,
            "parameters": parameters,
            "applianceType": device.appliance_type
        }
        _LOGGER.debug((f"Command sent (send_command): {command}"))

        url = f"{API_URL}/commands/v1/send"
        async with self._session.post(url, headers=self._headers, json=command) as resp:
            try:
                data = await resp.json()
                _LOGGER.debug((f"Command result (send_command): {data}"))
            except json.JSONDecodeError:
                _LOGGER.error("hOn Invalid Data ["+ str(resp.text()) + "] after sending command ["+ str(command)+ "]")
                return False
            if data["payload"]["resultCode"] == "0":
                return True
            _LOGGER.error("hOn command has been rejected. Error message ["+ str(data) + "] sent data ["+ str(command)+ "]")
        return False

    def get_device(self, hass, device_id):
        mac = get_hOn_mac(device_id, hass)
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac].device
        _LOGGER.error(f"Unable to find the device with ID: {device_id} and mac: {mac}")
        return None

def get_hOn_mac(device_id, hass):
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    return next(iter(device.identifiers))[1]

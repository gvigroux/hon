import asyncio
import logging
import voluptuous as vol
import aiohttp
import asyncio
import secrets
import json
import re
import ast
import time
import urllib.parse
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
    CONF_FRAMEWORK,
    CONF_COGNITO_TOKEN,
    CONF_REFRESH_TOKEN,
    AUTH_API,
    API_URL,
    APP_VERSION,
    OS_VERSION,
    OS,
    DEVICE_MODEL,
)

SESSION_TIMEOUT     = 21600 # 6 hours session

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
            self._framework = "None"
        else:
            self._email = entry.data[CONF_EMAIL]
            self._password = entry.data[CONF_PASSWORD]
            self._framework = entry.data.get(CONF_FRAMEWORK, "")
            self._id_token = entry.data.get(CONF_ID_TOKEN, "")
            self._refresh_token = entry.data.get(CONF_REFRESH_TOKEN, "")
            self._cognitoToken = entry.data.get(CONF_COGNITO_TOKEN, "")

        self._frontdoor_url = ""
        self._start_time    = time.time()

        self._header = headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        self._session = aiohttp.ClientSession(headers=self._header)
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
        coordinator = HonBaseCoordinator( self._hass, self, appliance)
        self._coordinator_dict[mac] = coordinator
        return coordinator


    async def async_get_frontdoor_url(self, error_code=0):
        data = (
            "message=%7B%22actions%22%3A%5B%7B%22id%22%3A%2279%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FLightningLoginCustomController%2FACTION%24login%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AloginForm%22%2C%22params%22%3A%7B%22username%22%3A%22"
            + urllib.parse.quote(self._email)
            + "%22%2C%22password%22%3A%22"
            + urllib.parse.quote(self._password)
            + "%22%2C%22startUrl%22%3A%22%22%7D%7D%5D%7D&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A%22"
            + urllib.parse.quote(self._framework)
            + "%22%2C%22app%22%3A%22siteforce%3AloginApp2%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce%3AloginApp2%22%3A%22YtNc5oyHTOvavSB9Q4rtag%22%7D%2C%22dn%22%3A%5B%5D%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Afalse%7D&aura.pageURI=%2FSmartHome%2Fs%2Flogin%2F%3Flanguage%3Dfr&aura.token=null"
        )
        async with self._session.post(
            "https://he-accounts.force.com/SmartHome/s/sfsites/aura?r=3&other.LightningLoginCustom.login=1",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("Unable to connect to the login service: " + str(resp.status))
                return False

            text = await resp.text()
            try:
                json_data = json.loads(text)
                self._frontdoor_url = json_data["events"][0]["attributes"]["values"]["url"]
            except:
                # Framework must be updated
                if text.find("clientOutOfSync") > 0 and error_code != 2:
                    start = text.find("Expected: ") + 10
                    end = text.find(" ", start)
                    _LOGGER.debug("Framework update from ["+ self._framework+ "] to ["+ text[start:end]+ "]")
                    self._framework = text[start:end]
                    return await self.async_get_frontdoor_url(2)
                _LOGGER.error("Unable to retreive the frontdoor URL. Message: " + text)
                return 1

        if error_code == 2 and self._entry != None:
            # Update Framework
            data = {**self._entry.data}
            data[CONF_FRAMEWORK] = self._framework
            self._hass.config_entries.async_update_entry(self._entry, data=data)

        return 0

    async def async_authorize(self):

        if await self.async_get_frontdoor_url(0) == 1:
            return False

        async with self._session.get(self._frontdoor_url) as resp:
            if resp.status != 200:
                _LOGGER.error("Unable to connect to the login service: " + str(resp.status))
                return False
            await resp.text()

        url = f"{AUTH_API}/apex/ProgressiveLogin?retURL=%2FSmartHome%2Fapex%2FCustomCommunitiesLanding"
        async with self._session.get(url) as resp:
            await resp.text()

        url = f"{AUTH_API}/services/oauth2/authorize?response_type=token+id_token&client_id=3MVG9QDx8IX8nP5T2Ha8ofvlmjLZl5L_gvfbT9.HJvpHGKoAS_dcMN8LYpTSYeVFCraUnV.2Ag1Ki7m4znVO6&redirect_uri=hon%3A%2F%2Fmobilesdk%2Fdetect%2Foauth%2Fdone&display=touch&scope=api%20openid%20refresh_token%20web&nonce=82e9f4d1-140e-4872-9fad-15e25fbf2b7c"
        async with self._session.get(url) as resp:
            text = await resp.text()
            array = []
            try:
                array = text.split("'", 2)

                if( len(array) == 1 ):
                    #Implement a second way to get the token value
                    m = re.search('id_token\=(.+?)&', text)
                    if m:
                        self._id_token = m.group(1)
                    else:
                        _LOGGER.error("Unable to get [id_token] during authorization process (tried both options). Full response [" + text + "]")
                        return False
                else:
                    params = urllib.parse.parse_qs(array[1])
                    self._id_token = params["id_token"][0]
            except:
                _LOGGER.error("Unable to get [id_token] during authorization process. Full response [" + text + "]")
                return False

        post_headers = {"Content-Type": "application/json", "id-token": self._id_token}
        data = {"mobileId": self._mobile_id,
                "os": OS,
                "osVersion": OS_VERSION,
                "appVersion": APP_VERSION,
                "deviceModel": DEVICE_MODEL}
        url = f"{API_URL}/auth/v1/login"
        async with self._session.post(url, headers=post_headers, json=data) as resp:
            try:
                json_data = await resp.json()
                self._cognitoToken = json_data["cognitoUser"]["Token"]
            except:
                _LOGGER.error("hOn Invalid Data ["+ str(resp.text()) + "] after sending command ["+ str(data)+ "] with headers []" + str(post_headers) + "]")
                return False


        url = f"{API_URL}/commands/v1/appliance"
        async with self._session.get(url,headers=self._headers) as resp:
            try:
                json_data = await resp.json()
            except:
                _LOGGER.error("hOn Invalid Data ["+ str(resp.text()) + "] after GET [" + url + "]")
                return False

            self._appliances = json_data["payload"]["appliances"]

            ''' Remove appliances with no mac'''
            self._appliances = [appliance for appliance in self._appliances if "macAddress" in appliance]
    
        self._start_time = time.time()
        return True

    '''
    async def async_get_state(self, mac, typeName, loop=False):

        # Create a new hOn session to avoid reaching the expiration
        elapsed_time = time.time() - self._start_time
        if( elapsed_time > SESSION_TIMEOUT ):
            self._session.cookie_jar.clear()
            await self.async_authorize()

        url = f"{API_URL}/commands/v1/context?macAddress={mac}&applianceType={typeName}&category=CYCLE"
        async with self._session.get(url, headers=self._headers) as resp:
            text = await resp.text()

            # Authentication has expired
            if resp.status == 403:
                if loop == True:
                    _LOGGER.error(f"Unable to get the state of the hOn device. HTTP code: {str(resp.status)} and text [{text}]")
                    return False
                await self.async_authorize()
                return await self.async_get_state(mac, typeName, True)

            elif resp.status != 200:
                _LOGGER.error(f"Unable to get the state of the hOn device. HTTP code: {str(resp.status)} and text [{text}]")
                return False

            full_json_data = json.loads(text)
            json_data = full_json_data["payload"]["shadow"]["parameters"]
            if "lastConnEvent" in full_json_data["payload"]:
                json_data["category"] = full_json_data["payload"]["lastConnEvent"].get("category")
            return json_data
        return False
        '''



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

        # Create a new hOn session to avoid reaching the expiration
        elapsed_time = time.time() - self._start_time
        if( elapsed_time > SESSION_TIMEOUT ):
            self._session.cookie_jar.clear()
            await self.async_authorize()

        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type,
            "category": "CYCLE"
        }
        url = f"{API_URL}/commands/v1/context"
        async with self._session.get(url, params=params, headers=self._headers) as response:
            json = await response.json()
            _LOGGER.debug(f"Context for mac[{device.mac_address}] type [{device.appliance_type}] {json}")
            return json.get("payload", {})

    async def load_statistics(self, device):
        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type
        }
        url = f"{API_URL}/commands/v1/statistics"
        async with self._session.get(url, params=params, headers=self._headers) as response:
            return (await response.json()).get("payload", {})

    @property
    def _headers(self):
        return {
            "Content-Type": "application/json",
            "cognito-token": self._cognitoToken,
            "id-token": self._id_token,
        }

    async def async_set(self, mac, typeName, parameters):

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = json.loads("{}")
        data["macAddress"] = mac
        data["commandName"] = "startProgram"
        data["applianceOptions"] = json.loads("{}")
        data["programName"] = "PROGRAMS." + typeName + ".HOME_ASSISTANT"
        data["ancillaryParameters"] = json.loads(
            '{"programFamily":"[standard]", "remoteActionable": "1", "remoteVisible": "1"}'
        )
        data["applianceType"] = typeName
        data["attributes"] = json.loads(
            '{"prStr":"HOME_ASSISTANT", "channel":"googleHome", "origin": "conversationalVoice"}'
        )
        if typeName == "WM":
            data["attributes"] = json.loads(
            '{"prStr":"HOME_ASSISTANT", "channel":"googleHome", "origin": "conversationalVoice", "energyLabel": "0"}'
        )
        data["device"] = json.loads(
            '{"mobileId":"xxxxxxxxxxxxxxxxxxx", "mobileOs": "android", "osVersion": "31", "appVersion": "1.53.4", "deviceModel": "lito"}'
        )
        data["parameters"] = parameters
        data["timestamp"] = timestamp
        data["transactionId"] = mac + "_" + data["timestamp"]

        async with self._session.post(f"{API_URL}/commands/v1/send",headers=self._headers,json=data,) as resp:
            try:
                json_data = await resp.json()
            except json.JSONDecodeError:
                _LOGGER.error("hOn Invalid Data ["+ str(resp.text()) + "] after sending command ["+ str(data)+ "]")
                return False
            if json_data["payload"]["resultCode"] == "0":
                return True
            _LOGGER.error("hOn command has been rejected. Error message ["+ str(json_data) + "] sent data ["+ str(data)+ "]")
        return False



    async def send_command(self, device, command, parameters, ancillary_parameters):
        now = datetime.utcnow().isoformat()
        data = {
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
        _LOGGER.debug(data)

        url = f"{API_URL}/commands/v1/send"
        async with self._session.post(url, headers=self._headers, json=data) as resp:
            try:
                json_data = await resp.json()
            except json.JSONDecodeError:
                _LOGGER.error("hOn Invalid Data ["+ str(resp.text()) + "] after sending command ["+ str(data)+ "]")
                return False
            if json_data["payload"]["resultCode"] == "0":
                return True
            _LOGGER.error("hOn command has been rejected. Error message ["+ str(json_data) + "] sent data ["+ str(data)+ "]")
        return False


def get_hOn_mac(device_id, hass):
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    return next(iter(device.identifiers))[1]
import asyncio
import logging
import voluptuous as vol
import aiohttp
import asyncio
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
)

SESSION_TIMEOUT     = 60

from .base import HonBaseCoordinator, HonBaseEntity

#class HonCoordinator(DataUpdateCoordinator):
#    def __init__(self, hass, hon, appliance):
#        """Initialize my coordinator."""
#        super().__init__(
#            hass,
#            _LOGGER,
#            name="hOn Coordinator",
#            update_interval=timedelta(seconds=15),
#        )
#        self._hon = hon
#        self._mac       = appliance["macAddress"]
#        self._type_name = appliance["applianceTypeName"]

#    async def _async_update_data(self):
#        return await self._hon.async_get_state(self._mac, self._type_name)




class HonConnection:
    def __init__(self, hass, entry, email = None, password = None) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator_dict  = {}

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
                _LOGGER.error(
                    "Unable to connect to the login service: " + str(resp.status)
                )
                return False

            text = await resp.text()
            try:
                json_data = json.loads(text)
                self._frontdoor_url = json_data["events"][0]["attributes"]["values"]["url"]
            except:
                """
                Maybe it's a framework update. Typical messages:
                */{"event":{"descriptor":"markup://aura:clientOutOfSync","eventDef":{"descriptor":"markup://aura:clientOutOfSync","t":"APPLICATION","xs":"I"}},"exceptionMessage":"Framework has been updated. Expected: tc2v9XbdIcEZ5G8cPbfJNQ Actual: 2yRFfs4WfGnFrNGn9C_dGg","exceptionEvent":true}/*ERROR*/
                */{"event":{"descriptor":"markup://aura:clientOutOfSync","eventDef":{"descriptor":"markup://aura:clientOutOfSync","t":"APPLICATION","xs":"I"}},"exceptionMessage":"Framework has been updated. Expected: -SjNAdgW9yv96YgKI8MiFA Actual: ","exceptionEvent":true}/*ERROR*/
                """
                if text.find("clientOutOfSync") > 0 and error_code != 2:
                    start = text.find("Expected: ") + 10
                    end = text.find(" ", start)
                    _LOGGER.info(
                        "Framework update from ["
                        + self._framework
                        + "] to ["
                        + text[start:end]
                        + "]"
                    )
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

        """async with self._session.get("https://he-accounts.force.com/SmartHome/s/login/?language=fr") as resp:
            wait_data = await resp.text()
            _LOGGER.warning(wait_data)"""

        """ **** Get FRONTDOOR URL *** """
        if await self.async_get_frontdoor_url(self._session) == 1:
            return False

        """ **** Connect to FRONTDOOR URL *** """
        async with self._session.get(self._frontdoor_url) as resp:
            if resp.status != 200:
                _LOGGER.error(
                    "Unable to connect to the login service: " + str(resp.status)
                )
                return False
            wait_data = await resp.text()

        """ **** Connect to ProgressiveLogin *** """
        async with self._session.get(
            "https://he-accounts.force.com/SmartHome/apex/ProgressiveLogin?retURL=%2FSmartHome%2Fapex%2FCustomCommunitiesLanding"
        ) as resp:
            wait_data = await resp.text()

        """ **** Get token *** """
        async with self._session.get(
            "https://he-accounts.force.com/SmartHome/services/oauth2/authorize?response_type=token+id_token&client_id=3MVG9QDx8IX8nP5T2Ha8ofvlmjLZl5L_gvfbT9.HJvpHGKoAS_dcMN8LYpTSYeVFCraUnV.2Ag1Ki7m4znVO6&redirect_uri=hon%3A%2F%2Fmobilesdk%2Fdetect%2Foauth%2Fdone&display=touch&scope=api%20openid%20refresh_token%20web&nonce=82e9f4d1-140e-4872-9fad-15e25fbf2b7c"
        ) as resp:
            text = await resp.text()
            array = []
            try:
                array = text.split("'", 2)

                if( len(array) == 1 ):
                    #Implement a second way to get the token value
                    m = re.search('id_token\=(.+?)&', text)
                    if m:
                        idt = m.group(1)
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
        data = '{"appVersion": "1.39.2","mobileId": "xxxxxxxxxxxxxxxxxx","osVersion": 30,"os": "android","deviceModel": "goldfish_x86"}'
        async with self._session.post(
            "https://api-iot.he.services/auth/v1/login", headers=post_headers, data=data
        ) as resp:
            text = await resp.text()
            try:
                json_data = json.loads(text)
                self._cognitoToken = json_data["cognitoUser"]["Token"]
            except:
                _LOGGER.error("Invalid JSON Data after POST to https://api-iot.he.services/auth/v1/login: " + text)
                return False
            #_LOGGER.warning(self._cognitoToken)

        credential_headers = {
            "cognito-token": self._cognitoToken,
            "id-token": self._id_token,
        }
        async with self._session.get(
            "https://api-iot.he.services/commands/v1/appliance",
            headers=credential_headers,
        ) as resp:
            text = await resp.text()
            try:
                json_data = json.loads(text)
            except:
                _LOGGER.error("No JSON Data after GET: " + text)
                return False

            self._appliances = json_data["payload"]["appliances"]
            
            # Add fake devices
            #self._appliances.append(ast.literal_eval("{'fwVersion': '3.8.0', 'applianceTypeId': 14, 'firstEnrollment': False, 'attributes': [{'parValue': '03.12.00', 'id': 98537740, 'parName': 'acuVersion', 'status': 1, 'lastUpdate': '2023-02-01T09:46:32Z'}, {'parValue': 'ESP32D0WDQ5', 'id': 98537739, 'parName': 'chipset', 'status': 1, 'lastUpdate': '2023-02-01T09:46:32Z'}, {'parValue': '167', 'id': 98538146, 'parName': 'dictionaryId', 'status': 1, 'lastUpdate': '2023-02-01T09:48:21Z'}, {'parValue': 'it-IT', 'id': 98537738, 'parName': 'lang', 'status': 1, 'lastUpdate': '2023-02-01T09:46:32Z'}], 'applianceModelId': 813, 'series': 'romania', 'firstEnrollmentTBC': False, 'code': '34004960', 'SK': 'app#34-86-xx-xx-34-90', 'macAddress': 'FAKE1', 'eepromName': 'no_eeprom', 'applianceId': '34-86-xx-xx-34-90#2023-02-01T09:46:20Z', 'id': 813, 'modelName': 'CCE4T620EB', 'applianceTypeName': 'REF', 'connectivity': 'wifi|ble', 'serialNumber': '340xxxxxxxx094', 'enrollmentDate': '2023-02-01T09:46:20.530Z', 'brand': 'candy', 'lastUpdate': '2023-02-01T09:46:32Z', 'eepromId': 41, 'applianceStatus': 1, 'coords': {'lng': 23.1265361, 'lat': 53.1144253}, 'PK': 'user#eu-west-1:75acd8ec-2457-47e8-82ef-d04bbbad9f72', 'sections': {'chatbot': True, 'epp_enabled': True, 'double_pairing_hidden': True}, 'topics': {'publish': [], 'subscribe': ['$aws/events/presence/disconnected/34-86-xx-xx-34-90', '$aws/events/presence/connected/34-86-xx-xx-34-90', 'haier/things/34-86-xx-xx-34-90/event/appliancestatus/update', 'haier/things/34-86-xx-xx-34-90/event/discovery/update']}}"))
            #self._appliances.append(ast.literal_eval("{'fwVersion': '3.8.0', 'applianceTypeId': 2, 'applianceModelId': 813, 'series': 'romania', 'code': '34004960', 'macAddress': 'FAKE2', 'eepromName': 'no_eeprom', 'applianceId': '34-86-xx-xx-34-90#2023-02-01T09:46:20Z', 'id': 813, 'modelName': 'CCE4T620EB', 'applianceTypeName': 'REF', 'connectivity': 'wifi|ble', 'serialNumber': '340xxxxxxxx094', 'enrollmentDate': '2023-02-01T09:46:20.530Z', 'brand': 'candy', 'lastUpdate': '2023-02-01T09:46:32Z', 'eepromId': 41, 'applianceStatus': 1}"))
            
            self._start_time = time.time()
            """for appliance in json_data['payload']['appliances']:
                _LOGGER.warning(appliance)
                if appliance.applianceTypeId == 11 :
                    self._appliances[]"""
        
        return True

    async def async_get_state(self, mac, typeName, returnAllData = False, loop=False):

        # Create a new hOn session to avoid going to expiration
        elapsed_time = time.time() - self._start_time
        if( elapsed_time > SESSION_TIMEOUT ):
            #TODO: async_get_frontdoor_url fails. I think because the session is already open.
            #I need to find a way to close or start a new session
            #await self.async_authorize()
            self._start_time = time.time()

        """
        if( mac == "FAKE1"):
            tmp = ast.literal_eval("{'payload': {'resultCode': '0', 'shadow': {'parameters': {'quickModeZ1': {'parNewVal': '0', 'lastUpdate': '2023-02-01T09:37:54Z'}, 'intelligenceMode': {'parNewVal': '1', 'lastUpdate': '2023-02-01T09:50:05Z'}, 'quickModeZ2': {'parNewVal': '0', 'lastUpdate': '2023-02-01T09:37:54Z'}, 'tempSelZ2': {'parNewVal': '-20', 'lastUpdate': '2023-02-01T09:37:54Z'}, 'holidayMode': {'parNewVal': '0', 'lastUpdate': '2023-02-01T09:37:54Z'}, 'tempSelZ1': {'parNewVal': '4', 'lastUpdate': '2023-02-01T09:37:54Z'}, 'errors': {'parNewVal': '00', 'lastUpdate': '2023-02-01T09:49:16Z'}, 'tempEnv': {'parNewVal': '21', 'lastUpdate': '2023-02-01T09:47:21Z'}, 'sterilizationStatus': {'parNewVal': '1', 'lastUpdate': '2023-02-01T09:37:54Z'}, 'doorStatusZ1': {'parNewVal': '0', 'lastUpdate': '2023-02-01T09:50:20Z'}}}, 'activity': {}, 'commandHistory': {'command': {'macAddress': 'FAKE2', 'commandName': 'startProgram', 'applianceOptions': {}, 'ancillaryParameters': {'programRules': {'fixedValue': {'tempSelZ1': {'@quickModeZ1': {'1': {'fixedValue': '1', 'typology': 'fixed'}}, '@intelligenceMode': {'1': {'fixedValue': '5', 'typology': 'fixed'}}, '@holidayMode': {'1': {'fixedValue': '17', 'typology': 'fixed'}}, '@quickModeZ2': {'1': {'fixedValue': '@tempSelZ1', 'typology': 'fixed'}}}, 'tempSelZ2': {'@quickModeZ1': {'1': {'fixedValue': '@tempSelZ2', 'typology': 'fixed'}}, '@intelligenceMode': {'1': {'fixedValue': '-18', 'typology': 'fixed'}}, '@holidayMode': {'1': {'fixedValue': '@tempSelZ2', 'typology': 'fixed'}}, '@quickModeZ2': {'1': {'fixedValue': '-24', 'typology': 'fixed'}}}}, 'typology': 'fixed', 'category': 'rule', 'mandatory': 0}}, 'applianceType': 'REF', 'attributes': {'prStr': 'PROGRAMS.REF.AUTO_SET', 'channel': 'mobileApp', 'origin': 'standardProgram'}, 'device': {'appVersion': '1.51.9', 'deviceModel': 'sdm845', 'osVersion': '29', 'mobileId': '814efd566ca3456a', 'mobileOs': 'android'}, 'parameters': {'intelligenceMode': '1'}, 'transactionId': '34-86-xx-xx-34-90_2023-02-01T09:49:58.494Z', 'timestamp': '2023-02-01T09:49:58.493Z'}, 'timestampAccepted': '2023-02-01T09:50:01.1Z', 'timestampExecuted': '2023-02-01T09:50:02.1Z'}, 'lastConnEvent': {'macAddress': 'FAKE1', 'category': 'CONNECTED', 'instantTime': '2023-02-01T09:49:09Z', 'timestampEvent': 1675244949030}}, 'authInfo': {}}")
            json_data = tmp["payload"]["shadow"]["parameters"]
            json_data_pay = tmp["payload"]
            if "lastConnEvent" in json_data_pay:
                json_data_lastCon = tmp["payload"]["lastConnEvent"]
                json_data.update(json_data_lastCon)
            return json_data
        if( mac == "FAKE2"):
            tmp = ast.literal_eval("{'payload': {'resultCode': '0', 'shadow': {'parameters': {'prCode': {'parNewVal': '0'}, 'prPhase': {'parNewVal': '1'}, 'prTime': {'parNewVal': '0'}, 'totalElectricityUsed': {'parNewVal': '-20'}, 'totalWashCycle': {'parNewVal': '0'}, 'totalWaterUsed': {'parNewVal': '4'}, 'actualWeight': {'parNewVal': '00'}, 'currentWaterUsed': {'parNewVal': '21'}, 'currentElectricityUsed': {'parNewVal': '10'}, 'dryLevel': {'parNewVal': '10'}, 'preFilterStatus': {'parNewVal': '10'}, 'mainFilterStatus': {'parNewVal': '10'},'airQuality': {'parNewVal': '10'}, 'coLevel': {'parNewVal': '10'}, 'vocValueIndoor': {'parNewVal': '10'}, 'pm2p5ValueIndoor': {'parNewVal': '10'}, 'pm10ValueIndoor': {'parNewVal': '10'}, 'humidityOutdoor': {'parNewVal': '10'}, 'humidityIndoor': {'parNewVal': '10'}, 'humidityZ1': {'parNewVal': '10'}, 'humidityZ2': {'parNewVal': '10'}, 'humidity': {'parNewVal': '10'}, 'remainingTimeMM': {'parNewVal': '10'}, 'tempZ2': {'parNewVal': '10'}, 'tempZ1': {'parNewVal': '10'}, 'temp': {'parNewVal': '10'}, 'spinSpeed': {'parNewVal': '10'}}},'lastConnEvent': {'macAddress': 'FAKE2', 'category': 'CONNECTED', 'instantTime': '2023-02-01T09:49:09Z', 'timestampEvent': 1675244949030}}}")
            json_data = tmp["payload"]["shadow"]["parameters"]
            json_data_pay = tmp["payload"]
            if "lastConnEvent" in json_data_pay:
                json_data_lastCon = tmp["payload"]["lastConnEvent"]
                json_data.update(json_data_lastCon)
            return json_data
        """

        credential_headers = {
            "cognito-token": self._cognitoToken,
            "id-token": self._id_token,
        }
        async with self._session.get(
            "https://api-iot.he.services/commands/v1/context?macAddress="
            + mac
            + "&applianceType="
            + typeName
            + "&category=CYCLE",
            headers=credential_headers,
        ) as resp:
            text = await resp.text()

            # Authentication has expired
            if resp.status == 403:
                # Do only one retry
                if loop == True:
                    _LOGGER.error(
                        "Unable to get the state of the hOn device. HTTP code: "
                        + str(resp.status)
                        + " and text["
                        + text
                        + "]"
                    )
                    return False
                await self.async_authorize()
                return await self.async_get_state(mac, typeName, returnAllData, True)

            elif resp.status != 200:
                _LOGGER.error(
                    "Unable to get the state of the hOn device. HTTP code: "
                    + str(resp.status)
                    + " and text["
                    + text
                    + "]"
                )
                return False
            #_LOGGER.warning(text)
            _LOGGER.info(text)

            if returnAllData:
                return json.loads(text)
            
            json_data = json.loads(text)["payload"]["shadow"]["parameters"]
            json_data_pay = json.loads(text)["payload"]
            if "lastConnEvent" in json_data_pay:
                json_data_lastCon = json.loads(text)["payload"]["lastConnEvent"]
                json_data.update(json_data_lastCon)

            #_LOGGER.warning(json_data)

            #json_data_activity = json.loads(text)["payload"]["activity"]
            #if( "attributes" in json_data_activity ):
            #    _LOGGER.warning(json.loads(text)["payload"]["activity"]["attributes"])

            return json_data
        return False



    #async def async_set_parameter(self, device_id, parameters):
    #    device_registry = dr.async_get(self._hass)
    #    device = device_registry.async_get(device_id)
    #    identifiers = next(iter(device.identifiers))

    #    entity_reg = er.async_get_registry(self._hass)
    #    entry = entity_reg.async_get(entity_id)

    #    dev_reg = dr.async_get_registry(hass)
    #    device = dev_reg.async_get(entry.device_id)

        #_LOGGER.warning(data)
        #return await self.async_set(identifiers[1], identifiers[2], parameters)


    async def async_set(self, mac, typeName, parameters):
        post_headers = {
            "Content-Type": "application/json",
            "cognito-token": self._cognitoToken,
            "id-token": self._id_token,
        }

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

        #_LOGGER.warning(data)
        async with self._session.post(
            "https://api-iot.he.services/commands/v1/send",
            headers=post_headers,
            json=data,
        ) as resp:
            #_LOGGER.warning(resp.status)
            text = await resp.text()
            # _LOGGER.warning(text)
            try:
                json_data = json.loads(text)
            except:
                _LOGGER.error(
                    "hOn Invalid Data ["
                    + text
                    + "] after sending command ["
                    + str(data)
                    + "]"
                )
                return False

            #_LOGGER.error(json_data)
            
            try:
                if json_data["payload"]["resultCode"] == "0":
                    return True
            except:
                return False


            _LOGGER.error(
                "hOn command has been rejected. Error message ["
                + text
                + "] sent data ["
                + str(data)
                + "]"
            )
        return False

def get_hOn_mac(device_id, hass):
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    return next(iter(device.identifiers))[1]
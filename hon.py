import asyncio
import logging
import voluptuous as vol
import aiohttp
import asyncio
import json
import urllib.parse
from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import (
    DOMAIN,
    CONF_ID_TOKEN,
    CONF_FRAMEWORK,
    CONF_COGNITO_TOKEN,
    CONF_REFRESH_TOKEN,
)


class HonConnection:
    def __init__(self, hass, entry) -> None:
        self._hass = hass
        self._entry = entry
        self._email = entry.data[CONF_EMAIL]
        self._password = entry.data[CONF_PASSWORD]

        self._framework = entry.data.get(CONF_FRAMEWORK, "")
        self._id_token = entry.data.get(CONF_ID_TOKEN, "")
        self._refresh_token = entry.data.get(CONF_REFRESH_TOKEN, "")
        self._cognitoToken = entry.data.get(CONF_COGNITO_TOKEN, "")

        self._frontdoor_url = ""

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        self._session = aiohttp.ClientSession(headers=headers)
        self._appliances = []


    @property
    def appliances(self):
        return self._appliances

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
                self._frontdoor_url = json_data["events"][0]["attributes"]["values"][
                    "url"
                ]
            except:
                """
                Maybe it's a framework update. Typical messages:
                */{"event":{"descriptor":"markup://aura:clientOutOfSync","eventDef":{"descriptor":"markup://aura:clientOutOfSync","t":"APPLICATION","xs":"I"}},"exceptionMessage":"Framework has been updated. Expected: tc2v9XbdIcEZ5G8cPbfJNQ Actual: 2yRFfs4WfGnFrNGn9C_dGg","exceptionEvent":true}/*ERROR*/
                */{"event":{"descriptor":"markup://aura:clientOutOfSync","eventDef":{"descriptor":"markup://aura:clientOutOfSync","t":"APPLICATION","xs":"I"}},"exceptionMessage":"Framework has been updated. Expected: -SjNAdgW9yv96YgKI8MiFA Actual: ","exceptionEvent":true}/*ERROR*/
                """
                if text.find("clientOutOfSync") > 0 and error_code != 2:
                    start = text.find("Expected: ") + 10
                    end = text.find(" ", start)
                    _LOGGER.warning(
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

        if error_code == 2:
            # Update Framework
            data = {**self._entry.data}
            data[CONF_FRAMEWORK] = self._framework
            self._hass.config_entries.async_update_entry(self._entry, data=data)

        return 0

    async def async_authorize(self):

        """async with self._session.get("https://he-accounts.force.com/SmartHome/s/login/?language=fr") as resp:
        wait_data = await resp.text()"""

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
            array = text.split("'", 2)
            params = urllib.parse.parse_qs(array[1])
            self._id_token = params["id_token"][0]

        post_headers = {"Content-Type": "application/json", "id-token": self._id_token}
        data = '{"appVersion": "1.39.2","mobileId": "xxxxxxxxxxxxxxxxxx","osVersion": 30,"os": "android","deviceModel": "goldfish_x86"}'
        async with self._session.post(
            "https://api-iot.he.services/auth/v1/login", headers=post_headers, data=data
        ) as resp:
            text = await resp.text()
            try:
                json_data = json.loads(text)
            except:
                _LOGGER.error("No JSON Data after POST: " + text)
                return False
            self._cognitoToken = json_data["cognitoUser"]["Token"]
            # _LOGGER.warning(self._cognitoToken)

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
            # _LOGGER.warning(self._appliances)

            """for appliance in json_data['payload']['appliances']:
                _LOGGER.warning(appliance)
                if appliance.applianceTypeId == 11 :
                    self._appliances[]"""
        return True

    async def async_get_state(self, mac, typeName, loop=False):
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
                return await self.async_get_state(mac, typeName, True)

            elif resp.status != 200:
                _LOGGER.error(
                    "Unable to get the state of the hOn device. HTTP code: "
                    + str(resp.status)
                    + " and text["
                    + text
                    + "]"
                )
                return False
            # _LOGGER.warning(text)

            json_data = json.loads(text)["payload"]["shadow"]["parameters"]
            return json_data
        return False

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
        data["device"] = json.loads(
            '{"mobileId":"xxxxxxxxxxxxxxxxxxx", "mobileOs": "android", "osVersion": "31", "appVersion": "1.41.2", "deviceModel": "lito"}'
        )
        data["parameters"] = parameters
        data["timestamp"] = timestamp
        data["transactionId"] = mac + "_" + data["timestamp"]

        # _LOGGER.warning(data)
        async with self._session.post(
            "https://api-iot.he.services/commands/v1/send",
            headers=post_headers,
            json=data,
        ) as resp:
            # _LOGGER.warning(resp.status)
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

            if json_data["payload"]["resultCode"] == "0":
                return True

            _LOGGER.error(
                "hOn command has been rejected. Error message ["
                + text
                + "] sent data ["
                + str(data)
                + "]"
            )
            # _LOGGER.warning(text)
            # _LOGGER.error("SEND Command response with code: " + str(resp.status) + " and text[" + text + "] after command: " + json.dumps(data))

        return False

"""hOn component constants."""

from enum import Enum, IntEnum
from homeassistant.components.climate.const import (
    FAN_OFF,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    SWING_OFF,
    SWING_BOTH,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    HVACMode,
)

DOMAIN = "hon"


CONF_ID_TOKEN = "token"
CONF_COGNITO_TOKEN = "cognito_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_FRAMEWORK = "framework"

PLATFORMS = [
    "climate", 
    "sensor",
    "binary_sensor",
    "button",
    "switch"
]

'''
    "select",
    "number" '''

AUTH_API        = "https://account2.hon-smarthome.com/SmartHome"
API_URL         = "https://api-iot.he.services"
APP_VERSION     = "2.0.10"
OS_VERSION      = 31
OS              = "android"
DEVICE_MODEL    = "exynos9820"



class APPLIANCE_TYPE(IntEnum):
    WASHING_MACHINE = 1,
    WASH_DRYER      = 2,
    OVEN            = 4,
    WINE_COOLER     = 6,
    PURIFIER        = 7,
    TUMBLE_DRYER    = 8,
    DISH_WASHER     = 9,
    CLIMATE         = 11,
    FRIDGE          = 14

APPLIANCE_DEFAULT_NAME = {
    "1": "Washing Machine",
    "2": "Wash Dryer",
    "4": "Oven",
    "6": "Wine Cooler",
    "7": "Purifier",
    "8": "Tumble Dryer",
    "9": "Dish Washer",
    "11": "Climate",
    "14": "Fridge",
}

CLIMATE_FAN_MODE = {
    FAN_OFF: "0",
    FAN_LOW: "3",
    FAN_MEDIUM: "2",
    FAN_HIGH: "1",
    FAN_AUTO: "5",
}

CLIMATE_HVAC_MODE = {
    HVACMode.AUTO: "0",
    HVACMode.COOL: "1",
    HVACMode.HEAT: "4",
    HVACMode.DRY: "2",
    HVACMode.FAN_ONLY: "6",
}

class ClimateSwingVertical:
    AUTO = "8"
    VERY_LOW = "7"
    LOW = "6"
    MIDDLE = "5"
    HIGH = "4"
    HEALTH_LOW = "3"
    VERY_HIGH = "2"
    HEALTH_HIGH = "1"

class ClimateSwingHorizontal:
    AUTO = "7"
    MIDDLE = "0"
    FAR_LEFT = "3"
    LEFT = "4"
    RIGHT = "5"
    FAR_RIGHT = "6"

class ClimateEcoPilotMode:
    OFF = "0"
    AVOID = "1"
    FOLLOW = "2"


#WASHING_MACHINE_DOOR_LOCK_STATUS = {
#    "1": "Locked",
#    "0": "Unlocked"
#}

#WASHING_MACHINE_PROGRAM = {
#    "0": { 
#        "name": "fragile",
#        "spinSpeed": "400",
#        "temp": "30",
#        "rinseIterations": "1",
#        "mainWashTime": "10",
#        "autoSoftenerStatus": "1"
#                },
#    "1": { 
#        "name": "quotidien sale",
#        "spinSpeed": "1400",
#        "temp": "40",
#        "rinseIterations": "2",
#        "mainWashTime": "15",
#        "autoSoftenerStatus": "1"
#                },
#}

#PURIFIER_LIGHT_VALUE  = {
#    "0": "Off",
#    "1": "50%",
#    "2": "100%"
#}

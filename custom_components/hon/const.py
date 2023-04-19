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
    "button"
]
'''
    "select",
    "number" '''


AUTH_API        = "https://he-accounts.force.com/SmartHome"
API_URL         = "https://api-iot.he.services"
APP_VERSION     = "1.53.7"
OS_VERSION      = 31
OS              = "android"
DEVICE_MODEL    = "goldfish_x86"



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


CLIMATE_MODE = {
    "0": "Auto",
    "1": "Cool",
    "2": "Dry",
    "4": "Heat",
    "6": "Fan only",
}

CLIMATE_FAN_MODE = {
    FAN_OFF: "0",
    FAN_LOW: "3",
    FAN_MEDIUM: "2",
    FAN_HIGH: "1",
    FAN_AUTO: "5",
}

'''
class ClimateHvacMode(IntEnum):
    HON_HVAC_AUTO = "0"
    HON_HVAC_COOL = "1"
    HON_HVAC_DRY = "2"
    HON_HVAC_HEAT = "4"
    HON_HVAC_FAN_ONLY = "6"'''

CLIMATE_HVAC_MODE = {
    HVACMode.AUTO: "0",
    HVACMode.COOL: "1",
    HVACMode.HEAT: "4",
    HVACMode.DRY: "2",
    HVACMode.FAN_ONLY: "6",
}

'''
CLIMATE_SWING_MODE_HORIZONTAL = {
    SWING_OFF: ClimateSwingHorizontal.MIDDLE,
    SWING_BOTH: ClimateSwingHorizontal.AUTO,
    SWING_HORIZONTAL: ClimateSwingHorizontal.AUTO,
    SWING_VERTICAL: ClimateSwingHorizontal.MIDDLE,
}'''

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


OVEN_PROGRAMS = {
    "3": "Botton",
    "4": "Bottom + fan",
    "6": "Convection + fan",
    "5": "Convectional",
    "10": "Taylor Bake",
    "23": "Multi-level",
    "54": "Soft+"
}

WASHING_MACHINE_DOOR_LOCK_STATUS = {
    "1": "Locked",
    "0": "Unlocked"
}

WASHING_MACHINE_ERROR_CODES = {
    "00": "No error",
    #"E1": "Error E1: Check the filter of the washing machine",
    "100000000000": "E2: Check if the door is closed",
    "8000000000000": "E4: Check the water supply",
    #"CLRF": "Error Clear Filter: Check the filter of the washing machine",
    "400000000000000": "Error Unb: Check the laundry, the washing machine might be overloaded",
    #"F3": "Error F3: Temperature sensor error",
    #"F4": "Error F4: Heating error",
    #"F7": "Error F7: Motor error",
    #"FA": "Error FA: Water level sensor error",
    #"FC0": "Error FC0: Communication error",
    #"FC1": "Error FC1: Communication error",
    #"FC2": "Error FC2: Communication error"
}

WASHING_MACHINE_MODE = {
    "0": "Disconnected",
    "1": "Ready",
    "2": "Running",
    "3": "Paused",
    "5": "Scheduled",
    "6": "Error",
    "7": "Finished"
}

WASHING_MACHINE_PROGRAM = {
    "0": { 
        "name": "fragile",
        "spinSpeed": "400",
        "temp": "30",
        "rinseIterations": "1",
        "mainWashTime": "10",
        "autoSoftenerStatus": "1"
                },
    "1": { 
        "name": "quotidien sale",
        "spinSpeed": "1400",
        "temp": "40",
        "rinseIterations": "2",
        "mainWashTime": "15",
        "autoSoftenerStatus": "1"
                },
}

DISH_WASHER_MODE = {
    "1": "Ready",
    "2": "Running",
    "3": "Delayed start",
    "5": "Delayed start cancelled",
    "7": "Finished",
    "9": "XXXXXX"
}

##some programs share id but parameters (T, W, time) might be differnet. Task develop parameter adjustment
DISH_WASHER_PROGRAMS = {
    "1": "program1",
    "2": "program2",
    "3": "Strong & Fast",
    "4": "program4",
    "5": "Dinner for 2",
    "6": "program6",
    "7": "program7",
    "8": "Eco 45ºC", ##happy hour, plastic & tupperware (75ºC & more water usage)
    "9": "Crystal", ##delicate 45ºC
    "10": "Class A 59' 65ºC", ##Pirex & Glassware
    "11": "Fast 29' 50ºC",
    "12": "Rinse",
    "13": "Crystal 45ºC",
    "14": "Auto Universal 65-75ºC",
    "15": "Auto Universal 50-60ºC", ##daily, special for pots
    "16": "Auto Sensor", ##dinner for 2, coctail glasses
    "17": "Ultra Silence 55ºC",
    "21": "Breakfast", #fast 39' 60ºC
    "22": "Sanitizing cycle",
    "23": "Baby Care", #super cleaning, vapor plus 75ºC
    "24": "Hygiene+ 75ºC",
}

TUMBLE_DRYER_MODE = {
    "1": "Ready",
    "2": "Running",
    "7": "Finished"
}

TUMBLE_DRYER_PROGRAMS = {
	"0": "Default",
	"62": "Cotton",
	"63": "Synthetics",
	"64": "Mix",
	"66": "Bed Sheets",
	"72": "Sports",
	"74": "i-time",
	"75": "Duvet",
	"76": "Wool",
	"78": "i-Refresh",
	"83": "Towel",
	"85": "Quick Dry",
	"92": "Delicate",
	"103": "Remote 103"
}

TUMBLE_DRYER_PROGRAMS_PHASE = {
	"0": "Waiting",
	"2": "Drying",
	"3": "Cooldown",
	"11": "11"
}

TUMBLE_DRYER_DRYL = {
	"3": "Cupboard dry",
	"12": "Ready to Iron H-3",
	"13": "Ready to Store H-2",
	"14": "Extra Dry H-1"
}

TUMBLE_DRYER_TEMPL = {
	"1": "Cool",
	"2": "Low temperature L-1",
	"3": "Middle temperature L-2",
	"4": "High temperature L-3"
}


PURIFIER_MODE = {
    "0": "Off",
    "1": "Sleep",
    "2": "Auto",
    "4": "Max"
}

PURIFIER_VOC_VALUE  = {
    "1": "Good",
    "2": "Moderate",
    "3": "Mediocre",
    "4": "Bad"
}
PURIFIER_LIGHT_VALUE  = {
    "0": "Off",
    "1": "50%",
    "2": "100%"
}

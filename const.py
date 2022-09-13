"""hOn component constants."""

from enum import IntEnum
from homeassistant.components.climate.const import (
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

# to store the cookie
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


CONF_ID_TOKEN = "token"
CONF_COGNITO_TOKEN = "cognito_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_FRAMEWORK = "framework"

PLATFORMS = [
    "climate",
    "sensor",
]


class ClimateFanMode(IntEnum):
    HON_FAN_OFF = 0
    HON_FAN_AUTO = 5
    HON_FAN_LOW = 3
    HON_FAN_MEDIUM = 2
    HON_FAN_HIGH = 1


class ClimateHvacMode(IntEnum):
    HON_HVAC_AUTO = 0
    HON_HVAC_COOL = 1
    HON_HVAC_DRY = 2
    HON_HVAC_HEAT = 4
    HON_HVAC_FAN_ONLY = 6


class ClimateSwingVertical(IntEnum):
    AUTO = 8
    VERY_LOW = 2
    LOW = 2
    MEDIUM = 4
    HIGH = 5
    VERY_HIGH = 6


class ClimateSwingHorizontal(IntEnum):
    AUTO = 7
    VERY_LOW = 0
    LOW = 3
    MEDIUM = 4
    HIGH = 5
    VERY_HIGH = 6


CLIMATE_FAN_MODE = {
    FAN_LOW: ClimateFanMode.HON_FAN_LOW.value,
    FAN_MEDIUM: ClimateFanMode.HON_FAN_MEDIUM.value,
    FAN_HIGH: ClimateFanMode.HON_FAN_HIGH.value,
    FAN_AUTO: ClimateFanMode.HON_FAN_AUTO.value,
}

CLIMATE_HVAC_MODE = {
    HVACMode.AUTO: ClimateHvacMode.HON_HVAC_AUTO,
    HVACMode.COOL: ClimateHvacMode.HON_HVAC_COOL,
    HVACMode.HEAT: ClimateHvacMode.HON_HVAC_HEAT,
    HVACMode.DRY: ClimateHvacMode.HON_HVAC_DRY,
    HVACMode.FAN_ONLY: ClimateHvacMode.HON_HVAC_FAN_ONLY,
}

CLIMATE_SWING_MODE_HORIZONTAL = {
    SWING_OFF: ClimateSwingHorizontal.MEDIUM,
    SWING_BOTH: ClimateSwingHorizontal.AUTO,
    SWING_HORIZONTAL: ClimateSwingHorizontal.AUTO,
    SWING_VERTICAL: ClimateSwingHorizontal.MEDIUM,
}


OVEN_PROGRAMS = {
    "3": "Botton",
    "4": "Bottom + fan",
    "6": "Convection + fan",
    "5": "Convectional",
    "10": "Taylor Bake",
    "23": "Multi-level",
    "54": "Soft+",
}

WASHING_MACHINE_MODE = {
    "1": "Ready",
    "2": "Running",
    "7": "Finished"
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
	"11": "11",
}

TUMBLE_DRYER_DRYL = {
	"3": "Cupboard dry",
	"12": "Extra Dry H-1",
	"13": "Ready to Store H-2",
	"14": "Ready to Iron H-3"
}

TUMBLE_DRYER_TEMPL = {
	"1": "Cool",
	"2": "Low temperature L-1",
	"3": "Middle temperature L-2",
	"4": "High temperature L-3"
}


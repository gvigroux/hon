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

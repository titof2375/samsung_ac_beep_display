"""Constants for Samsung AC SmartThings integration."""

DOMAIN = "samsung_ac_st"
CONF_TOKEN = "token"

ST_API_BASE = "https://api.smartthings.com/v1"
POLL_INTERVAL = 30  # seconds

# SmartThings capabilities
CAP_SWITCH = "switch"
CAP_AC_MODE = "airConditionerMode"
CAP_COOL_SETPOINT = "thermostatCoolingSetpoint"
CAP_HEAT_SETPOINT = "thermostatHeatingSetpoint"
CAP_TEMP = "temperatureMeasurement"
CAP_HUMIDITY = "relativeHumidityMeasurement"
CAP_FAN_MODE = "airConditionerFanMode"
CAP_SWING = "fanOscillationMode"
CAP_EXECUTE = "execute"

# OCF execute path for display/beep
OCF_PATH = "mode/vs/0"
# Samsung naming is intentionally inverted for display!
OPT_DISPLAY_OFF = "Light_On"   # Light_On = display OFF
OPT_DISPLAY_ON  = "Light_Off"  # Light_Off = display ON
OPT_BEEP_ON     = "Beep_On"
OPT_BEEP_OFF    = "Beep_Off"

# AC mode mapping: HA → SmartThings
HA_TO_ST_MODE = {
    "cool":     "cool",
    "heat":     "heat",
    "auto":     "auto",
    "fan_only": "wind",
    "dry":      "dry",
}
ST_TO_HA_MODE = {v: k for k, v in HA_TO_ST_MODE.items()}

# Fan mode mapping
HA_TO_ST_FAN = {
    "auto":   "auto",
    "low":    "low",
    "medium": "medium",
    "high":   "high",
    "turbo":  "turbo",
}
ST_TO_HA_FAN = {v: k for k, v in HA_TO_ST_FAN.items()}

# Swing mode mapping
HA_TO_ST_SWING = {
    "off":      "fixed",
    "vertical": "vertical",
    "horizontal": "horizontal",
    "both":     "all",
}
ST_TO_HA_SWING = {v: k for k, v in HA_TO_ST_SWING.items()}

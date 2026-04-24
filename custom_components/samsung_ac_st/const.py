"""Constants for Samsung AC SmartThings integration."""

DOMAIN = "samsung_ac_st"
CONF_TOKEN = "token"

ST_API_BASE = "https://api.smartthings.com/v1"
POLL_INTERVAL = 30  # seconds

# SmartThings capabilities
CAP_SWITCH           = "switch"
CAP_AC_MODE          = "airConditionerMode"
CAP_OPTIONAL_MODE    = "custom.airConditionerOptionalMode"
CAP_COOL_SETPOINT    = "thermostatCoolingSetpoint"
CAP_TEMP             = "temperatureMeasurement"
CAP_HUMIDITY         = "relativeHumidityMeasurement"
CAP_FAN_MODE         = "airConditionerFanMode"
CAP_SWING            = "fanOscillationMode"
CAP_AUDIO_VOLUME     = "audioVolume"
CAP_AUTO_CLEANING    = "custom.autoCleaningMode"
CAP_DUST_FILTER      = "custom.dustFilter"
CAP_DUST_ALARM       = "samsungce.dustFilterAlarm"
CAP_TROPICAL_NIGHT   = "custom.airConditionerTropicalNightMode"
CAP_EXECUTE          = "execute"

# OCF execute — Samsung naming (display est inversé !)
OCF_PATH        = "mode/vs/0"
OPT_DISPLAY_OFF = "Light_On"   # Light_On  = écran éteint
OPT_DISPLAY_ON  = "Light_Off"  # Light_Off = écran allumé

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
    "off":        "fixed",
    "vertical":   "vertical",
    "horizontal": "horizontal",
    "both":       "all",
}
ST_TO_HA_SWING = {v: k for k, v in HA_TO_ST_SWING.items()}

# Optional mode (Wind-Free etc.)
OPTIONAL_MODES = ["off", "sleep", "quiet", "speed", "windFree", "windFreeSleep"]

# Filter status icons
FILTER_STATUS_ICONS = {
    "normal":  "mdi:air-filter",
    "wash":    "mdi:alert",
    "replace": "mdi:alert-circle",
}

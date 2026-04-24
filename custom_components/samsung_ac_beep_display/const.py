"""Constants for Samsung AC Beep & Display integration."""

DOMAIN = "samsung_ac_beep_display"

CONF_TOKEN = "token"

ST_API_BASE = "https://api.smartthings.com/v1"
POLL_INTERVAL = 30  # seconds

# SmartThings capabilities used
CAP_EXECUTE = "execute"
CAP_AC_LIGHTING = "samsungce.airConditionerLighting"
CAP_SOUND_MODE = "samsungce.soundMode"
CAP_AC_MODE = "airConditionerMode"

# OCF execute path for Samsung AC custom options
OCF_PATH = "mode/vs/0"

# Option values (note: Samsung naming is inverted for Light!)
OPT_LIGHT_ON = "Light_On"    # counter-intuitive: this turns display OFF
OPT_LIGHT_OFF = "Light_Off"  # counter-intuitive: this turns display ON
OPT_BEEP_ON = "Beep_On"      # enables beep sound
OPT_BEEP_OFF = "Beep_Off"    # disables beep sound

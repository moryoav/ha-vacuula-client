"""Constants for the Vacuula Client integration."""

from homeassistant.const import Platform

DOMAIN = "vacuula"
NAME = "Vacuula Client"
CONF_URL = "url"
# Vacuula 1.1 defaults to app port 8050; discovery preserves other actual ports.
DEFAULT_URL = "http://vacuula.local:8050"
GEN3 = "neato.gen3"
GEN4 = "neato.gen4"
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VACUUM,
]

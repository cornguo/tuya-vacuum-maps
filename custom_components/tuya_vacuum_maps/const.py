"""This module defines global constants"""

DOMAIN = "tuya_vacuum_maps"

CONF_SERVER = "server"
CONF_TUYA_LOCAL_ENTRY = "tuya_local_entry"
# Option: add area cleaning to the vacuum's Tuya Local entity
CONF_AREA_CLEANING = "area_cleaning"

# Domain of the Tuya Local integration (github.com/make-all/tuya-local)
TUYA_LOCAL_DOMAIN = "tuya_local"

CONF_SERVER_CHINA = "https://openapi.tuyacn.com"
CONF_SERVER_WEST_AMERICA = "https://openapi.tuyaus.com"
CONF_SERVER_EAST_AMERICA = "https://openapi-ueaz.tuyaus.com"
CONF_SERVER_CENTRAL_EUROPE = "https://openapi.tuyaeu.com"
CONF_SERVER_WEST_EUROPE = "https://openapi-weaz.tuyaeu.com"
CONF_SERVER_INDIA = "https://openapi.tuyain.com"
CONF_SERVER_SINGAPORE = "https://openapi-sg.iotbing.com"

CONF_SERVERS = {
    CONF_SERVER_CHINA: "China",
    CONF_SERVER_WEST_AMERICA: "Western America",
    CONF_SERVER_EAST_AMERICA: "Eastern America",
    CONF_SERVER_CENTRAL_EUROPE: "Central Europe",
    CONF_SERVER_WEST_EUROPE: "Western Europe",
    CONF_SERVER_INDIA: "India",
    CONF_SERVER_SINGAPORE: "Singapore",
}

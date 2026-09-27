"""Handle Home Assistant config flow for the Tuya Vacuum Maps integration."""

import logging
from typing import Any, override

import tuya_vacuum
from tuya_vacuum.tuya import (
    CrossRegionAccessError,
    InvalidClientIDError,
    InvalidClientSecretError,
    InvalidDeviceIDError,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_NAME,
)

from .const import (
    CONF_SERVER,
    CONF_SERVER_WEST_AMERICA,
    CONF_SERVERS,
    CONF_TUYA_LOCAL_ENTRY,
    DOMAIN,
    TUYA_LOCAL_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def validate_input(data: dict) -> None:
    """Validate that the user input allows us to connect.

    This makes blocking network calls, so run it in the executor.
    """

    vacuum = tuya_vacuum.TuyaVacuum(
        data["server"], data["client_id"], data["client_secret"], data["device_id"]
    )

    vacuum.fetch_realtime_map()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya Vacuum Maps."""

    # Schema version of the entries it creates
    # Home Assistant will call the migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        # Form defaults, pre-filled when importing from a Tuya Local device
        self._defaults: dict[str, str] = {
            CONF_NAME: "Vacuum Map",
            CONF_DEVICE_ID: "",
        }

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """This is Invoked when a user initiates a flow via the user interface.

        Also called when discovered but a matching discovery step is not defined.
        """

        # Offer to reuse a device already set up in Tuya Local
        if self._tuya_local_entries():
            return self.async_show_menu(
                step_id="user",
                menu_options={
                    "tuya_local": "Use a device from Tuya Local",
                    "manual": "Enter device details manually",
                },
            )

        return await self.async_step_manual()

    def _tuya_local_entries(self) -> list[config_entries.ConfigEntry]:
        """Return the config entries of the Tuya Local integration."""
        return self.hass.config_entries.async_entries(TUYA_LOCAL_DOMAIN)

    async def async_step_tuya_local(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Pick a Tuya Local device to pre-fill the device ID and name."""

        entries = {entry.entry_id: entry for entry in self._tuya_local_entries()}

        if user_input is not None:
            entry = entries[user_input[CONF_TUYA_LOCAL_ENTRY]]
            data = {**entry.data, **entry.options}
            # Sub-devices behind a hub are addressed in the cloud by their own ID
            self._defaults = {
                CONF_NAME: f"{entry.title} Map",
                CONF_DEVICE_ID: data.get("device_cid") or data[CONF_DEVICE_ID],
            }
            return await self.async_step_manual()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TUYA_LOCAL_ENTRY): vol.In(
                    {entry_id: entry.title for entry_id, entry in entries.items()}
                ),
            }
        )

        return self.async_show_form(step_id="tuya_local", data_schema=data_schema)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Enter the server, credentials and device details."""

        # List of errors related to the form
        errors = {}

        if user_input is not None:
            try:
                try:
                    await self.hass.async_add_executor_job(
                        validate_input, user_input
                    )

                    # Process the information
                    return self.async_create_entry(
                        title=user_input.pop(CONF_NAME), data=user_input
                    )
                except Exception as err:
                    _LOGGER.error("Error occurred while validating: %s", err)
                    raise err
            except CrossRegionAccessError:
                errors[CONF_SERVER] = (
                    "Cross region access is not allowed, data center mismatch."
                )
            except InvalidClientIDError:
                errors[CONF_CLIENT_ID] = "Invalid Client ID."
            except InvalidClientSecretError:
                errors[CONF_CLIENT_SECRET] = "Invalid Client Secret."
            except InvalidDeviceIDError:
                errors[CONF_DEVICE_ID] = "Invalid Device ID."
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "Unknown error occurred."
        # Define the schema of the form
        data_schema = vol.Schema(
            {
                # Device Name
                vol.Required(CONF_NAME, default=self._defaults[CONF_NAME]): str,
                # Server API URL
                vol.Required(CONF_SERVER, default=CONF_SERVER_WEST_AMERICA): vol.In(
                    CONF_SERVERS
                ),
                # Client ID
                vol.Required(CONF_CLIENT_ID, default=""): str,
                # Client Secret
                vol.Required(CONF_CLIENT_SECRET, default=""): str,
                # Device ID
                vol.Required(
                    CONF_DEVICE_ID, default=self._defaults[CONF_DEVICE_ID]
                ): str,
            }
        )

        return self.async_show_form(
            step_id="manual", data_schema=data_schema, errors=errors
        )

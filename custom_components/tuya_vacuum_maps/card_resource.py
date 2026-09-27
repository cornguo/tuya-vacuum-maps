"""Load the rooms card on dashboards.

The card is added to the dashboard resources (Settings > Dashboards >
Resources) when they're managed in the UI. Resources come with the dashboard
configuration, so a browser or app showing a cached Home Assistant page still
loads the card; a script added to the page itself with add_extra_js_url is
missing from such a cached page, and dashboards then show "Custom element
doesn't exist". The resources are reached through Home Assistant's lovelace
integration (hass.data["lovelace"]), so if that fails, or dashboards use YAML
resources, the card is added to the page instead.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

LOVELACE_DOMAIN = "lovelace"
STORAGE_MODE = "storage"


def _storage_resources(hass: HomeAssistant):
    """Return the dashboard resources if they're managed in the UI."""
    lovelace = hass.data.get(LOVELACE_DOMAIN)
    if getattr(lovelace, "resource_mode", None) != STORAGE_MODE:
        return None
    return getattr(lovelace, "resources", None)


def _matching_items(resources, card_url: str) -> list[dict]:
    """Return the resources for the card, with any version."""
    return [
        item
        for item in resources.async_items()
        if item.get("url", "").split("?")[0] == card_url
    ]


def _add_extra_js_url(hass: HomeAssistant, url: str) -> None:
    """Add the card to the Home Assistant page itself."""
    # Imported here, so the module can be tested without Home Assistant
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    add_extra_js_url(hass, url)


async def async_register_card(hass: HomeAssistant, card_url: str, version: str) -> None:
    """Load the card on dashboards, as a resource if possible.

    @param card_url: Where the card is served, e.g. "/domain/card.js".
    @param version: Changes with the card, so browsers don't keep an old one.
    """
    url = f"{card_url}?v={version}"
    resources = _storage_resources(hass)
    if resources is not None:
        try:
            # Loads the resources from storage if needed
            await resources.async_get_info()
            items = _matching_items(resources, card_url)
            if not items:
                await resources.async_create_item({"res_type": "module", "url": url})
            elif items[0]["url"] != url:
                await resources.async_update_item(
                    items[0]["id"], {"res_type": "module", "url": url}
                )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Could not add the rooms card to the dashboard resources, "
                "loading it with the page instead: %s",
                err,
            )
        else:
            return

    _LOGGER.info(
        "Dashboard resources aren't managed in the UI; if the rooms card shows "
        "\"Custom element doesn't exist\", add %s as a JavaScript module resource",
        card_url,
    )
    _add_extra_js_url(hass, url)


async def async_unregister_card(hass: HomeAssistant, card_url: str) -> None:
    """Remove the card from the dashboard resources."""
    resources = _storage_resources(hass)
    if resources is None:
        return
    try:
        await resources.async_get_info()
        for item in _matching_items(resources, card_url):
            await resources.async_delete_item(item["id"])
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning("Could not remove the rooms card resource: %s", err)

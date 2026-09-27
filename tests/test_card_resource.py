"""Tests for loading the rooms card on dashboards."""

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "card_resource",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "card_resource.py",
)
card_resource = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(card_resource)

CARD_URL = "/tuya_vacuum_maps/card.js"


class FakeResources:
    """Behave like Home Assistant's ResourceStorageCollection."""

    def __init__(self, items: list[dict] | None = None) -> None:
        self._stored = items or []
        self.loaded = False
        self.items: list[dict] = []

    async def async_get_info(self) -> dict:
        if not self.loaded:
            self.items = [dict(item) for item in self._stored]
            self.loaded = True
        return {"resources": len(self.items)}

    def async_items(self) -> list[dict]:
        return self.items

    async def async_create_item(self, data: dict) -> dict:
        item = {"id": f"id{len(self.items)}", "type": data["res_type"], "url": data["url"]}
        self.items.append(item)
        return item

    async def async_update_item(self, item_id: str, updates: dict) -> dict:
        item = next(item for item in self.items if item["id"] == item_id)
        item.update(type=updates["res_type"], url=updates["url"])
        return item

    async def async_delete_item(self, item_id: str) -> None:
        self.items = [item for item in self.items if item["id"] != item_id]


def _hass(resources, mode: str = "storage") -> SimpleNamespace:
    return SimpleNamespace(
        data={"lovelace": SimpleNamespace(resource_mode=mode, resources=resources)}
    )


@pytest.fixture
def page_scripts(monkeypatch) -> list[str]:
    """Record scripts added to the Home Assistant page instead."""
    added: list[str] = []
    monkeypatch.setattr(
        card_resource, "_add_extra_js_url", lambda hass, url: added.append(url)
    )
    return added


def test_card_is_added_as_a_resource(page_scripts):
    """With UI-managed resources the card becomes a module resource."""
    resources = FakeResources([{"id": "other", "type": "module", "url": "/x.js"}])

    asyncio.run(card_resource.async_register_card(_hass(resources), CARD_URL, "v1"))

    assert resources.items[-1] == {"id": "id1", "type": "module", "url": f"{CARD_URL}?v=v1"}
    assert page_scripts == []


def test_changed_card_updates_its_resource(page_scripts):
    """A new version replaces the old resource instead of adding another."""
    resources = FakeResources([{"id": "a", "type": "module", "url": f"{CARD_URL}?v=v1"}])

    asyncio.run(card_resource.async_register_card(_hass(resources), CARD_URL, "v2"))

    assert resources.items == [{"id": "a", "type": "module", "url": f"{CARD_URL}?v=v2"}]


def test_yaml_resources_load_the_card_with_the_page(page_scripts):
    """Resources defined in YAML can't be changed, so the page loads it."""
    resources = FakeResources()

    asyncio.run(
        card_resource.async_register_card(_hass(resources, "yaml"), CARD_URL, "v1")
    )

    assert page_scripts == [f"{CARD_URL}?v=v1"]
    assert resources.items == []


def test_failing_resources_load_the_card_with_the_page(page_scripts):
    """If the resources can't be changed, e.g. after a change in Home
    Assistant, the card is still loaded."""

    class BrokenResources(FakeResources):
        async def async_create_item(self, data):
            raise KeyError("res_type")

    for hass in (_hass(BrokenResources()), SimpleNamespace(data={})):
        asyncio.run(card_resource.async_register_card(hass, CARD_URL, "v1"))

    assert page_scripts == [f"{CARD_URL}?v=v1"] * 2


def test_unregister_removes_only_the_card():
    """Removing the integration removes its resource and no other."""
    resources = FakeResources(
        [
            {"id": "a", "type": "module", "url": f"{CARD_URL}?v=v1"},
            {"id": "b", "type": "module", "url": "/x.js"},
        ]
    )

    asyncio.run(card_resource.async_unregister_card(_hass(resources), CARD_URL))

    assert [item["id"] for item in resources.items] == ["b"]

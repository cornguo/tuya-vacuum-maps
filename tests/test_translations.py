"""Tests for the integration's translations."""

import json
from pathlib import Path
import re

import pytest

_DIR = Path(__file__).parent.parent / "custom_components" / "tuya_vacuum_maps"
LANGUAGES = ["en", "zh-Hant"]


def _translations(language: str) -> dict:
    return json.loads((_DIR / "translations" / f"{language}.json").read_text("utf-8"))


def _keys(data: dict, prefix: str = "") -> set[str]:
    """Return the dotted paths of all texts."""
    keys = set()
    for key, value in data.items():
        path = f"{prefix}{key}"
        keys |= _keys(value, f"{path}.") if isinstance(value, dict) else {path}
    return keys


def _source(name: str) -> str:
    return (_DIR / name).read_text("utf-8")


def test_languages_have_the_same_texts():
    """Every text is translated in every language."""
    en = _keys(_translations("en"))
    for language in LANGUAGES:
        assert _keys(_translations(language)) == en, language


@pytest.mark.parametrize("language", LANGUAGES)
def test_placeholders_match_english(language):
    """Translations keep the placeholders filled in by the code."""
    en = _translations("en")
    other = _translations(language)

    def texts(data, prefix=""):
        for key, value in data.items():
            if isinstance(value, dict):
                yield from texts(value, f"{prefix}{key}.")
            else:
                yield f"{prefix}{key}", value

    other_texts = dict(texts(other))
    for key, text in texts(en):
        assert set(re.findall(r"{\w+}", other_texts[key])) == set(
            re.findall(r"{\w+}", text)
        ), (language, key)


def test_config_flow_texts_exist():
    """Menu options and error keys used by the config flow are translated."""
    config = _translations("en")["config"]
    source = _source("config_flow.py")

    menu_options = re.search(r"menu_options=\[([^\]]*)\]", source).group(1)
    for option in re.findall(r'"(\w+)"', menu_options):
        assert option in config["step"]["user"]["menu_options"]

    errors = re.findall(r'errors\[[^\]]+\] = "(\w+)"', source)
    assert errors
    for error in errors:
        assert error in config["error"]


def test_options_flow_texts_exist():
    """Every option of the options flow is labelled and described."""
    step = _translations("en")["options"]["step"]["init"]
    schema = _source("config_flow.py").split("OPTIONS_SCHEMA = ", 1)[1]
    schema = schema.split("\n)\n", 1)[0]
    values = dict(
        re.findall(
            r'^(CONF_\w+) = "(\w+)"',
            _source("const.py") + _source("polling.py"),
            re.MULTILINE,
        )
    )
    names = re.findall(r"vol\.Required\(\s*(CONF_\w+)", schema)
    options = [values[name] for name in names]
    assert len(options) == 3
    for option in options:
        assert option in step["data"]
        assert option in step["data_description"]


def test_entity_and_exception_texts_exist():
    """Translation keys used by entities and errors are translated."""
    en = _translations("en")
    for platform in ("button", "number", "sensor"):
        for key in re.findall(
            r'_attr_translation_key = "(\w+)"', _source(f"{platform}.py")
        ):
            assert key in en["entity"][platform]

    for name in ("button.py", "coordinator.py"):
        for key in re.findall(r'translation_key="(\w+)"', _source(name)):
            assert key in en["exceptions"]

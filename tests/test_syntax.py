"""Check that every module of the integration compiles.

Modules that import Home Assistant, such as the entity platforms, aren't
imported by the other tests, so a syntax error in them would go unnoticed.
"""

from pathlib import Path

import pytest

_MODULES = sorted(
    (Path(__file__).parent.parent / "custom_components" / "tuya_vacuum_maps").glob(
        "*.py"
    )
)


@pytest.mark.parametrize("path", _MODULES, ids=lambda path: path.name)
def test_module_compiles(path: Path):
    """The module has no syntax error."""
    compile(path.read_text(encoding="utf-8"), str(path), "exec")

import json
from pathlib import Path

import pytest

from tools.init_rev_c_trail_armor_session import initialize


def test_initializer_creates_non_authoritative_inert_armor_workspace(tmp_path: Path):
    session = tmp_path / "armor-a"
    report = initialize(session)

    assert report["physical_authority"] is False
    assert report["impact_energy_authority"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authorized"] is False

    manifest = json.loads((session / "trail_armor_manifest.json").read_text())
    assert manifest["scope"] == "rev_c_inert_trail_armor_trial"
    assert manifest["live_battery_present"] is False
    assert manifest["electrical_energy_present"] is False
    assert manifest["powered_vehicle"] is False
    assert manifest["impact_energy_qualified"] is False


def test_initializer_refuses_to_overwrite_existing_armor_session(tmp_path: Path):
    session = tmp_path / "armor-a"
    session.mkdir()
    marker = session / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(session)

    assert marker.read_text(encoding="utf-8") == "keep"

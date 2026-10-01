import json
from pathlib import Path

import pytest

from tools.init_rev_c_charge_dock_session import initialize


def test_initializer_creates_inert_private_dock_workspace(tmp_path: Path):
    session = tmp_path / "dock-01"
    report = initialize(session)

    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False
    assert report["live_battery_test_authorized"] is False
    assert report["electrical_charge_authorized"] is False
    assert report["powered_operation_authorized"] is False

    manifest = json.loads((session / "dock_manifest.json").read_text())
    assert manifest["scope"] == "rev_c_passive_charge_cradle_mechanical_trial"
    assert manifest["electrical_energy_present"] is False
    assert manifest["charger_energized"] is False
    assert manifest["electrical_charge_authorized"] is False

    workspace = json.loads((session / "workspace_manifest.json").read_text())
    assert workspace["manifest"] == "dock_manifest.json"
    assert "inert" in workspace["next_step"].lower()


def test_initializer_refuses_to_overwrite_existing_session(tmp_path: Path):
    session = tmp_path / "dock-01"
    session.mkdir()
    marker = session / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(session)

    assert marker.read_text(encoding="utf-8") == "keep"

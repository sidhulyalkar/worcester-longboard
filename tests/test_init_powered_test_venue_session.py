import json
from pathlib import Path

import pytest

from tools.init_powered_test_venue_session import initialize


def test_initializer_creates_non_authoritative_private_venue_workspace(tmp_path: Path):
    session = tmp_path / "venue-01"
    report = initialize(session)

    assert report["venue_permission_authority"] is False
    assert report["vehicle_powered_operation_authority"] is False
    assert report["public_operation_authority"] is False
    assert report["dog_accompanied_operation_authority"] is False

    manifest = json.loads((session / "venue_manifest.json").read_text())
    assert manifest["scope"] == "x1_powered_test_venue_record"
    assert manifest["vehicle_powered_operation_authority"] is False
    assert manifest["dog_accompanied_operation_authority"] is False

    workspace = json.loads((session / "workspace_manifest.json").read_text())
    assert workspace["manifest"] == "venue_manifest.json"
    assert "not treat this workspace as vehicle authority" in workspace["next_step"]


def test_initializer_refuses_to_overwrite_existing_venue_session(tmp_path: Path):
    session = tmp_path / "venue-01"
    session.mkdir()
    marker = session / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(session)

    assert marker.read_text(encoding="utf-8") == "keep"

import json
from pathlib import Path

import pytest

from tools.init_x1_lifecycle_health import initialize
from tools.new_x1_health_event import create_event


def test_initializer_creates_private_health_workspace_scaffold(tmp_path: Path):
    workspace = tmp_path / "health"
    report = initialize(
        workspace,
        "X1-TEST-A",
        "CFG-A",
        "2026-10-01T12:00:00Z",
    )

    assert report["health_authority"] is False
    assert report["powered_operation_authority"] is False
    assert report["public_operation_authority"] is False
    assert report["dog_accompanied_operation_authority"] is False

    registry = json.loads((workspace / "component_registry.json").read_text())
    assert registry["board_id"] == "X1-TEST-A"
    assert registry["configuration_id"] == "CFG-A"
    assert registry["components"] == []
    assert (workspace / "events").is_dir()
    assert (workspace / "event_template.json").is_file()


def test_initializer_refuses_to_overwrite_existing_workspace(tmp_path: Path):
    workspace = tmp_path / "health"
    workspace.mkdir()
    marker = workspace / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(
            workspace,
            "X1-TEST-A",
            "CFG-A",
            "2026-10-01T12:00:00Z",
        )

    assert marker.read_text(encoding="utf-8") == "keep"


def test_event_generator_uses_registry_identity_and_supports_config_override(tmp_path: Path):
    workspace = tmp_path / "health"
    initialize(
        workspace,
        "X1-TEST-A",
        "CFG-A",
        "2026-10-01T12:00:00Z",
    )
    registry = workspace / "component_registry.json"

    out = workspace / "events" / "0001.json"
    event = create_event(
        registry,
        out,
        "PREFLIGHT-01",
        "2026-10-01T12:10:00Z",
        "PREFLIGHT",
        "UNPOWERED_CONTROLLED_TEST",
        "CFG-B",
    )
    assert event["board_id"] == "X1-TEST-A"
    assert event["configuration_id"] == "CFG-B"
    assert event["event_type"] == "PREFLIGHT"
    assert event["powered_operation_authorized"] is False


def test_event_generator_refuses_overwrite(tmp_path: Path):
    workspace = tmp_path / "health"
    initialize(
        workspace,
        "X1-TEST-A",
        "CFG-A",
        "2026-10-01T12:00:00Z",
    )
    registry = workspace / "component_registry.json"
    out = workspace / "events" / "0001.json"
    create_event(
        registry,
        out,
        "BASELINE-01",
        "2026-10-01T12:10:00Z",
        "BASELINE",
        "UNPOWERED_BENCH",
    )

    with pytest.raises(FileExistsError):
        create_event(
            registry,
            out,
            "BASELINE-02",
            "2026-10-01T12:20:00Z",
            "BASELINE",
            "UNPOWERED_BENCH",
        )

import hashlib
import json
from pathlib import Path

import pytest

from tools.init_x1_lifecycle_health import initialize
from tools.new_x1_health_event import create_event


def _stamp(doc):
    payload = json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _write_chassis(tmp_path: Path, *, qualified=True):
    chassis = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rolling_chassis_physical",
            "qualified": qualified,
            "powered_operation_authorized": False,
        }
    )
    path = tmp_path / "chassis_authority.json"
    path.write_text(json.dumps(chassis), encoding="utf-8")
    return path, chassis


def test_initializer_creates_private_health_workspace_scaffold(tmp_path: Path):
    chassis_path, chassis = _write_chassis(tmp_path)
    workspace = tmp_path / "health"
    report = initialize(
        workspace,
        "X1-TEST-A",
        "CFG-A",
        "2026-10-01T12:00:00Z",
        chassis_path,
    )

    assert report["health_authority"] is False
    assert report["powered_operation_authority"] is False
    assert report["public_operation_authority"] is False
    assert report["dog_accompanied_operation_authority"] is False
    assert (
        report["rolling_chassis_fingerprint_sha256"]
        == chassis["authority_fingerprint_sha256"]
    )

    registry = json.loads((workspace / "component_registry.json").read_text())
    assert registry["board_id"] == "X1-TEST-A"
    assert registry["configuration_id"] == "CFG-A"
    assert registry["components"] == []
    assert (
        registry["upstream_authorities"]["rolling_chassis_fingerprint_sha256"]
        == chassis["authority_fingerprint_sha256"]
    )
    assert (workspace / "events").is_dir()
    assert (workspace / "event_template.json").is_file()


def test_initializer_rejects_invalid_authority_without_leaving_workspace(tmp_path: Path):
    chassis_path, _ = _write_chassis(tmp_path, qualified=False)
    workspace = tmp_path / "health"

    with pytest.raises(ValueError, match="fingerprint-valid"):
        initialize(
            workspace,
            "X1-TEST-A",
            "CFG-A",
            "2026-10-01T12:00:00Z",
            chassis_path,
        )

    assert not workspace.exists()


def test_initializer_refuses_to_overwrite_existing_workspace(tmp_path: Path):
    chassis_path, _ = _write_chassis(tmp_path)
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
            chassis_path,
        )

    assert marker.read_text(encoding="utf-8") == "keep"


def test_event_generator_uses_registry_identity_and_supports_config_override(tmp_path: Path):
    chassis_path, _ = _write_chassis(tmp_path)
    workspace = tmp_path / "health"
    initialize(
        workspace,
        "X1-TEST-A",
        "CFG-A",
        "2026-10-01T12:00:00Z",
        chassis_path,
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
    chassis_path, _ = _write_chassis(tmp_path)
    workspace = tmp_path / "health"
    initialize(
        workspace,
        "X1-TEST-A",
        "CFG-A",
        "2026-10-01T12:00:00Z",
        chassis_path,
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

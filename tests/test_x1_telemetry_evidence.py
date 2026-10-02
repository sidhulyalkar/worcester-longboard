import csv
import hashlib
import json
from pathlib import Path

from tools.generate_synthetic_x1_telemetry import generate
from tools.summarize_x1_commissioning_telemetry import summarize
from tools.validate_x1_telemetry_session import validate_session

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads(
    (ROOT / "hardware/x1_telemetry_signal_registry.json").read_text()
)
SNAPSHOT = json.loads(
    (ROOT / "hardware/rev_c_telemetry_snapshot_2026-10-02.json").read_text()
)


def _load_fixture(tmp_path: Path, stage="RIDER_ONLY_VERY_LOW_SPEED"):
    paths = generate(tmp_path / "session", stage)
    manifest = Path(paths["manifest"])
    power = json.loads(Path(paths["power_architecture"]).read_text())
    health = json.loads(Path(paths["pre_health"]).read_text())
    return manifest, power, health


def _validate(manifest: Path, power: dict, health: dict):
    return validate_session(
        manifest,
        power_architecture=power,
        pre_health=health,
        registry=REGISTRY,
        snapshot=SNAPSHOT,
    )[0]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage4_fixture_validates_and_replays_required_measurements(tmp_path: Path):
    manifest, power, health = _load_fixture(tmp_path)
    report = _validate(manifest, power, health)
    assert report["valid"] is True
    assert report["commissioning_evidence_ready"] is True
    assert report["powered_operation_authorized"] is False
    assert report["common_overlap"]["fraction_of_shortest_required_stream"] >= 0.9

    replay = summarize(
        manifest,
        power_architecture=power,
        pre_health=health,
        registry=REGISTRY,
        snapshot=SNAPSHOT,
    )
    assert replay["valid"] is True
    assert {x["metric_id"] for x in replay["measurements"]} == set(
        SNAPSHOT["stage_requirements"]["RIDER_ONLY_VERY_LOW_SPEED"][
            "required_measurements"
        ]
    )
    assert replay["metric_details"]["remote_release_propulsion_decay_s"]["value"] >= 0
    assert replay["metric_details"]["longitudinal_jerk_mps3"]["value"] > 0
    assert replay["metric_details"]["stopping_distance_m"]["value"] > 0
    assert replay["powered_operation_authorized"] is False


def test_stage1_motor_speed_is_alias_of_raw_erpm(tmp_path: Path):
    manifest, power, health = _load_fixture(
        tmp_path,
        stage="SECURED_UNLOADED_SPIN",
    )
    replay = summarize(
        manifest,
        power_architecture=power,
        pre_health=health,
        registry=REGISTRY,
        snapshot=SNAPSHOT,
    )
    assert replay["valid"] is True
    assert replay["metric_details"]["left_motor_speed"]["field"] == "left_motor_erpm"
    assert replay["metric_details"]["right_motor_speed"]["field"] == "right_motor_erpm"


def test_file_tamper_breaks_hash_integrity(tmp_path: Path):
    manifest, power, health = _load_fixture(tmp_path)
    with (manifest.parent / "control.csv").open("a", encoding="utf-8") as handle:
        handle.write("tampered\n")
    report = _validate(manifest, power, health)
    assert report["valid"] is False
    assert any("file sha256 mismatch" in x for x in report["errors"])


def test_timestamp_regression_fails_even_with_updated_hash(tmp_path: Path):
    manifest, power, health = _load_fixture(tmp_path)
    data = json.loads(manifest.read_text())
    stream = next(x for x in data["streams"] if x["stream_id"] == "control")
    path = manifest.parent / stream["file_path"]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    fields = list(rows[0].keys())
    rows[10]["session_time_s"] = rows[8]["session_time_s"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    stream["sha256"] = _sha(path)
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    report = _validate(manifest, power, health)
    assert report["valid"] is False
    assert any("session_time_s must be strictly increasing" in x for x in report["errors"])


def test_sequence_drop_requires_exact_accounting(tmp_path: Path):
    manifest, power, health = _load_fixture(tmp_path)
    data = json.loads(manifest.read_text())
    stream = next(x for x in data["streams"] if x["stream_id"] == "control")
    path = manifest.parent / stream["file_path"]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    fields = list(rows[0].keys())
    rows.pop(10)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    stream["sha256"] = _sha(path)
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    report = _validate(manifest, power, health)
    assert report["valid"] is False
    assert any("sequence gaps imply 1" in x for x in report["errors"])


def test_declared_source_can_validate_but_not_support_commissioning(tmp_path: Path):
    manifest, power, health = _load_fixture(tmp_path)
    data = json.loads(manifest.read_text())
    data["sources"][0]["qualification_status"] = "DECLARED"
    data["sources"][0]["calibration_evidence_ref"] = ""
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    report = _validate(manifest, power, health)
    assert report["valid"] is True
    assert report["commissioning_evidence_ready"] is False
    assert any("not QUALIFIED" in x for x in report["readiness_blockers"])


def test_excessive_clock_uncertainty_blocks_commissioning_readiness(tmp_path: Path):
    manifest, power, health = _load_fixture(tmp_path)
    data = json.loads(manifest.read_text())
    data["clocks"][0]["synchronization_uncertainty_s"] = 0.05
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    report = _validate(manifest, power, health)
    assert report["valid"] is True
    assert report["commissioning_evidence_ready"] is False
    assert any("synchronization uncertainty" in x for x in report["readiness_blockers"])


def test_logger_cannot_become_control_dependency(tmp_path: Path):
    manifest, power, health = _load_fixture(tmp_path)
    data = json.loads(manifest.read_text())
    data["logger_contract"]["realtime_control_dependency"] = True
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    report = _validate(manifest, power, health)
    assert report["valid"] is False
    assert "logger cannot be a realtime control dependency" in report["errors"]

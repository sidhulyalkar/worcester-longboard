import copy
import hashlib
import json

from tools.init_dummy_pack_session import build_manifest
from tools.qualify_dummy_pack_mount import qualify as qualify_dummy
from tools.qualify_power_packaging_candidate import qualify as qualify_candidate

G = 9.80665


def _stamp(doc):
    payload = json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _candidate_manifest():
    return {
        "schema_version": 1,
        "scope": "power_packaging_candidate_definition",
        "powered_operation_authorized": False,
        "brake_drive_topology_authority_fingerprint_sha256": "a" * 64,
        "rev_b_template_authority_fingerprint_sha256": "b" * 64,
        "pack_mass_target_kg": 4.0,
        "pack_mass_tolerance_kg": 0.25,
        "enclosure_envelope_mm": {"length": 420.0, "width": 180.0, "height": 75.0},
        "target_cg_local_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
        "cg_tolerance_mm": {"x": 10.0, "y": 10.0, "z": 10.0},
        "mounting_region": "center deck reference region",
        "service_removal_direction": "upward after service fasteners removed",
        "positive_retention_concept": "through-fastened load spreaders with positive locking",
        "load_spreading_concept": "distributed rails/plates across verified deck structure",
        "skid_guard_concept": "replaceable lower sacrificial skid below vulnerable enclosure",
        "minimum_vulnerable_component_ground_keepout_mm": 35.0,
        "static_load_requirements": {
            "front_fraction_min": 0.35,
            "front_fraction_max": 0.65,
            "left_fraction_min": 0.35,
            "left_fraction_max": 0.65,
        },
    }


def _candidate():
    report = qualify_candidate(_candidate_manifest())
    assert report["qualified"] is True
    return report


def _chassis():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rolling_chassis_physical",
            "scope": "unpowered_rolling_chassis_only",
            "qualified": True,
            "errors": [],
            "powered_operation_authorized": False,
        }
    )


def _complete_dummy_manifest():
    candidate = _candidate()
    chassis = _chassis()
    data = build_manifest(candidate, chassis, "DUMMY-ENC-A", "DUMMY-MOUNT-A")
    bare_mass = 12.0
    dummy_mass = 4.0
    installed_mass = bare_mass + dummy_mass
    data["measurements"].update(
        {
            "dummy_mass_kg": dummy_mass,
            "dummy_cg_local_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
            "bare_system_mass_kg": bare_mass,
            "dummy_installed_system_mass_kg": installed_mass,
            "wheel_loads_n": {
                "bare": {pos: bare_mass * G / 4.0 for pos in ("fl", "fr", "rl", "rr")},
                "dummy_installed": {pos: installed_mass * G / 4.0 for pos in ("fl", "fr", "rl", "rr")},
            },
            "minimum_vulnerable_component_ground_clearance_mm": 50.0,
        }
    )
    for key in data["checks"]:
        data["checks"][key] = True
    return data, candidate, chassis


def test_power_packaging_candidate_is_inert_only_and_fingerprinted():
    report = _candidate()
    assert report["authority"] == "x1_power_packaging_candidate"
    assert report["powered_operation_authorized"] is False
    unsigned = dict(report)
    fingerprint = unsigned.pop("authority_fingerprint_sha256")
    expected = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    assert fingerprint == expected


def test_candidate_rejects_cg_outside_enclosure():
    manifest = _candidate_manifest()
    manifest["target_cg_local_mm"]["x"] = 500.0
    report = qualify_candidate(manifest)
    assert report["qualified"] is False
    assert any("outside enclosure" in x for x in report["errors"])


def test_complete_inert_dummy_pack_mount_qualifies():
    data, candidate, chassis = _complete_dummy_manifest()
    report = qualify_dummy(data, candidate, chassis)
    assert report["qualified"] is True
    assert report["authority"] == "x1_dummy_pack_mount"
    assert report["powered_operation_authorized"] is False
    assert abs(report["derived_static_loads"]["front_fraction"] - 0.5) < 1e-9
    assert abs(report["derived_static_loads"]["left_fraction"] - 0.5) < 1e-9


def test_dummy_mass_outside_candidate_tolerance_fails():
    data, candidate, chassis = _complete_dummy_manifest()
    data["measurements"]["dummy_mass_kg"] = 5.0
    report = qualify_dummy(data, candidate, chassis)
    assert report["qualified"] is False
    assert any("dummy mass outside" in x for x in report["errors"])


def test_four_corner_load_mismatch_fails():
    data, candidate, chassis = _complete_dummy_manifest()
    data["measurements"]["wheel_loads_n"]["dummy_installed"]["fl"] *= 2.0
    report = qualify_dummy(data, candidate, chassis)
    assert report["qualified"] is False
    assert any("wheel-load" in x for x in report["errors"])


def test_static_load_bias_outside_candidate_window_fails():
    data, candidate, chassis = _complete_dummy_manifest()
    total = data["measurements"]["dummy_installed_system_mass_kg"] * G
    data["measurements"]["wheel_loads_n"]["dummy_installed"] = {
        "fl": 0.35 * total,
        "fr": 0.35 * total,
        "rl": 0.15 * total,
        "rr": 0.15 * total,
    }
    report = qualify_dummy(data, candidate, chassis)
    assert report["qualified"] is False
    assert any("front load fraction" in x for x in report["errors"])


def test_structural_or_witness_failure_fails():
    data, candidate, chassis = _complete_dummy_manifest()
    data["checks"]["no_witness_mark_movement"] = False
    report = qualify_dummy(data, candidate, chassis)
    assert report["qualified"] is False
    assert any("no_witness_mark_movement" in x for x in report["errors"])


def test_tampered_candidate_authority_is_rejected():
    data, candidate, chassis = _complete_dummy_manifest()
    bad = copy.deepcopy(candidate)
    bad["pack_mass_target_kg"] = 5.0
    report = qualify_dummy(data, bad, chassis)
    assert report["qualified"] is False
    assert any("fingerprint" in x or "snapshot drift" in x for x in report["errors"])

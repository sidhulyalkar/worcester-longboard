import csv
import json
from pathlib import Path

from tools.compare_snowdeck_signatures import compare, load_signature
from tools.summarize_snowdeck_force_log import summarize


def write_force_log(path: Path, bias: float = 0.0) -> None:
    fieldnames = [
        "trial_id",
        "pose",
        "left_heel",
        "left_forefoot",
        "right_heel",
        "right_forefoot",
    ]
    poses = {
        "NEUTRAL": (30, 20, 28, 22),
        "DEEP_KNEE": (28, 24, 26, 24),
        "HEEL_BIASED": (38, 12, 36, 14),
        "TOE_BIASED": (18, 32, 16, 34),
    }
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for trial_index in range(3):
            jitter = trial_index * 0.5
            for pose, values in poses.items():
                for sample_index in range(4):
                    sample_jitter = sample_index * 0.1
                    row = {
                        "trial_id": f"trial-{trial_index+1:02d}",
                        "pose": pose,
                        "left_heel": values[0] + jitter + sample_jitter,
                        "left_forefoot": values[1] + bias + sample_jitter,
                        "right_heel": values[2] + jitter + sample_jitter,
                        "right_forefoot": values[3] + bias + sample_jitter,
                    }
                    writer.writerow(row)


def complete_session(path: Path, condition_id: str) -> None:
    trial = {
        "independent_remount": True,
        "neutral_pose_recorded": True,
        "deep_knee_pose_recorded": True,
        "heel_biased_pose_recorded": True,
        "toe_biased_pose_recorded": True,
        "emergency_step_off_clear": True,
        "unexpected_rocking_observed": False,
        "insert_or_fastener_migration_observed": False,
        "fixture_interference_observed": False,
        "persistent_deformation_observed": False,
        "overload_stop_contact_observed": False,
        "private_force_log_ref": "private.csv",
    }
    data = {
        "schema_version": 1,
        "scope": "x1_snowdeck_reversible_bench_observation",
        "session_id": "TEST-" + condition_id,
        "condition_id": condition_id,
        "trials": [
            {"id": "trial-01", **trial},
            {"id": "trial-02", **trial},
            {"id": "trial-03", **trial},
        ],
        "post_trial_inspection": {
            "fastener_migration_observed": False,
            "insert_shift_observed": False,
            "fixture_damage_observed": False,
            "residual_deformation_observed": False,
        },
        "fabrication_authority": False,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_snowdeck_signature_is_descriptive_and_fail_closed(tmp_path):
    force = tmp_path / "force.csv"
    session = tmp_path / "session.json"
    write_force_log(force)
    complete_session(session, "S0")

    report = summarize(force, session)

    assert report["trial_count"] == 3
    assert report["mechanical_rejects"] == []
    assert report["eligible_for_further_bench_comparison"] is True
    assert report["heel_to_toe_forefoot_transfer"]["left"]["mean"] > 0
    assert report["heel_to_toe_forefoot_transfer"]["right"]["mean"] > 0
    assert report["physical_authority"] is False
    assert report["fabrication_authority"] is False
    assert report["ride_authority"] is False
    assert report["powered_operation_authorized"] is False


def test_mechanical_reject_blocks_progression_but_preserves_vector(tmp_path):
    force = tmp_path / "force.csv"
    session = tmp_path / "session.json"
    write_force_log(force)
    complete_session(session, "C1")
    data = json.loads(session.read_text())
    data["trials"][1]["unexpected_rocking_observed"] = True
    session.write_text(json.dumps(data), encoding="utf-8")

    report = summarize(force, session)

    assert report["eligible_for_further_bench_comparison"] is False
    assert any("rocking" in item for item in report["mechanical_rejects"])
    assert "neutral" in report


def test_pairwise_comparison_reports_deltas_without_winner(tmp_path):
    base_force = tmp_path / "base.csv"
    variant_force = tmp_path / "variant.csv"
    base_session = tmp_path / "base_session.json"
    variant_session = tmp_path / "variant_session.json"
    write_force_log(base_force, bias=0.0)
    write_force_log(variant_force, bias=3.0)
    complete_session(base_session, "S0")
    complete_session(variant_session, "S1")

    baseline = summarize(base_force, base_session)
    variant = summarize(variant_force, variant_session)
    report = compare(baseline, variant)

    assert report["winner_selected"] is False
    assert report["physical_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert "neutral_left_forefoot_mean" in report["signed_variant_minus_baseline"]


def test_signature_loader_rejects_authoritative_claim(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({
        "scope": "x1_snowdeck_bench_signature",
        "physical_authority": True,
        "powered_operation_authorized": False,
    }), encoding="utf-8")

    try:
        load_signature(path)
    except ValueError as exc:
        assert "non-authoritative" in str(exc)
    else:
        raise AssertionError("authoritative SnowDeck signature must be rejected")

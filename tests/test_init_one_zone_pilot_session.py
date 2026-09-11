import argparse

import pytest

from tools.init_one_zone_pilot_session import build_manifest


def _args():
    return argparse.Namespace(
        load_cell_id="LC-A",
        hx711_id="ADC-A",
        pod_id="POD-A",
        zone_pad_id="PAD-A",
        channel="left_heel",
        sps=10,
        calibration_mass_kg=[5.013, 1.997, 10.021],
        validation_mass_kg=7.486,
    )


def test_initializer_manifest_starts_safely_unqualified():
    m = build_manifest(_args())
    assert m["hardware_ids"]["load_cell_id"] == "LC-A"
    assert m["hx711_sps"] == 10
    assert m["acquisition"]["rate_jumper_verified"] is False
    assert m["mechanical"]["vendor_pattern_verified"] is False
    assert m["mechanical"]["stop_gap_unloaded_mm"] is None


def test_initializer_uses_actual_sorted_mass_sequence():
    m = build_manifest(_args())
    kinds = [row["kind"] for row in m["observations"]]
    assert kinds == [
        "zero_pre", "load_up", "load_up", "load_up",
        "load_down", "load_down", "zero_post",
    ]
    ups = [row["mass_kg"] for row in m["observations"] if row["kind"] == "load_up"]
    downs = [row["mass_kg"] for row in m["observations"] if row["kind"] == "load_down"]
    assert ups == [1.997, 5.013, 10.021]
    assert downs == [5.013, 1.997]
    assert m["validation"][0]["mass_kg"] == 7.486
    assert m["validation"][0]["log"] == "raw/validation_7p486kg.csv"


def test_initializer_requires_three_unique_masses():
    args = _args()
    args.calibration_mass_kg = [2.0, 5.0]
    with pytest.raises(ValueError, match="at least three"):
        build_manifest(args)
    args.calibration_mass_kg = [2.0, 5.0, 5.0]
    with pytest.raises(ValueError, match="unique"):
        build_manifest(args)


def test_initializer_rejects_nonindependent_or_oversize_validation():
    args = _args()
    args.validation_mass_kg = 5.013
    with pytest.raises(ValueError, match="independent"):
        build_manifest(args)
    args = _args()
    args.validation_mass_kg = 20.1
    with pytest.raises(ValueError, match="hard 20 kg"):
        build_manifest(args)

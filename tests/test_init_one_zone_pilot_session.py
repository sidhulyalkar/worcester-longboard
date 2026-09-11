import argparse
import json

from tools.init_one_zone_pilot_session import build_manifest


def _args():
    return argparse.Namespace(
        load_cell_id="LC-A",
        hx711_id="ADC-A",
        pod_id="POD-A",
        zone_pad_id="PAD-A",
        channel="left_heel",
        sps=10,
    )


def test_initializer_manifest_starts_safely_unqualified():
    m = build_manifest(_args())
    assert m["hardware_ids"]["load_cell_id"] == "LC-A"
    assert m["hx711_sps"] == 10
    assert m["acquisition"]["rate_jumper_verified"] is False
    assert m["mechanical"]["vendor_pattern_verified"] is False
    assert m["mechanical"]["stop_gap_unloaded_mm"] is None


def test_initializer_uses_required_load_sequence():
    m = build_manifest(_args())
    kinds = [row["kind"] for row in m["observations"]]
    assert kinds == [
        "zero_pre", "load_up", "load_up", "load_up",
        "load_down", "load_down", "zero_post",
    ]
    assert [row["mass_kg"] for row in m["observations"] if row["kind"] == "load_up"] == [2.0, 5.0, 10.0]
    assert m["validation"][0]["mass_kg"] == 7.5

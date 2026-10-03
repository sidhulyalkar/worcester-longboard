import json
from pathlib import Path

from cad.generate_rev_c_deck_templates import CANDIDATES

ROOT = Path(__file__).resolve().parents[1]


def test_rev_c_deck_candidate_envelopes_match_generator():
    template = json.loads(
        (ROOT / "hardware" / "rev_c_deck_comparison_private_template.json").read_text()
    )
    by_id = {candidate["id"]: candidate for candidate in template["candidates"]}

    expected = {
        "comp95_class": CANDIDATES["comp95"],
        "pro_warren_iii_class": CANDIDATES["pro_warren_iii"],
        "agent_class": CANDIDATES["agent"],
    }

    assert set(by_id) == set(expected)

    for candidate_id, source in expected.items():
        envelope = by_id[candidate_id]["reference_envelope_mm"]
        assert envelope["length"] == int(source["length_mm"])
        assert envelope["width"] == int(source["width_mm"])

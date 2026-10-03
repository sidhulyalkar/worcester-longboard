import json

from cad.generate_rev_c_deck_templates import CANDIDATES, generate_blinded


def test_blinded_deck_templates_hide_product_identity_and_preserve_geometry(tmp_path):
    out_dir = tmp_path / "blind"
    key_path = tmp_path / "key.json"
    order = ["agent", "comp95", "pro_warren_iii"]

    paths, key = generate_blinded(out_dir, key_path, candidate_order=order)

    assert [path.name for path in paths] == [
        "rev_c_candidate_a_blind.svg",
        "rev_c_candidate_b_blind.svg",
        "rev_c_candidate_c_blind.svg",
    ]
    assert key["mapping"]["A"]["candidate_id"] == "agent"
    assert key["mapping"]["A"]["width_mm"] == 284
    assert key["physical_authority"] is False
    assert key["powered_operation_authorized"] is False

    for label, path in zip(("A", "B", "C"), paths):
        text = path.read_text(encoding="utf-8")
        assert f"Candidate {label}" in text
        assert "Product identity intentionally hidden" in text
        for name, spec in CANDIDATES.items():
            assert spec["label"] not in text

    loaded = json.loads(key_path.read_text(encoding="utf-8"))
    assert loaded == key


def test_blinded_deck_templates_reject_incomplete_candidate_order(tmp_path):
    try:
        generate_blinded(
            tmp_path / "blind",
            tmp_path / "key.json",
            candidate_order=["agent", "comp95", "comp95"],
        )
    except ValueError as exc:
        assert "each Rev-C deck candidate exactly once" in str(exc)
    else:
        raise AssertionError("invalid blind order must be rejected")

from pathlib import Path

from cad.generate_rev_c_deck_templates import CANDIDATES, generate, svg_for


def test_rev_c_candidate_envelopes_match_published_reference_dimensions():
    assert CANDIDATES["comp95"]["length_mm"] == 950.0
    assert CANDIDATES["comp95"]["width_mm"] == 251.0
    assert CANDIDATES["pro_warren_iii"]["length_mm"] == 980.0
    assert CANDIDATES["pro_warren_iii"]["width_mm"] == 244.0
    assert CANDIDATES["agent"]["length_mm"] == 1020.0
    assert CANDIDATES["agent"]["width_mm"] == 284.0


def test_svg_is_explicitly_non_structural():
    svg = svg_for("comp95", CANDIDATES["comp95"])
    assert "NOT structural CAD" in svg
    assert 'width="990.0mm"' in svg
    assert 'height="291.0mm"' in svg


def test_generator_writes_all_candidate_templates(tmp_path: Path):
    paths = generate(tmp_path)
    assert {p.name for p in paths} == {
        "rev_c_comp95_deck_envelope.svg",
        "rev_c_pro_warren_iii_deck_envelope.svg",
        "rev_c_agent_deck_envelope.svg",
    }
    assert all(p.exists() for p in paths)

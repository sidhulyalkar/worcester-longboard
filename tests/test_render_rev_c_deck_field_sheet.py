from tools.render_rev_c_deck_field_sheet import render


def test_deck_field_sheet_is_blinded_and_has_three_trials_each():
    text = render()

    assert "Candidate A" in text
    assert "Candidate B" in text
    assert "Candidate C" in text
    assert "comp95" not in text.lower()
    assert "warren" not in text.lower()
    assert "agent" not in text.lower()
    assert text.count("| 1 | [ ] | [ ] | [ ] | [ ] |") == 3
    assert text.count("| 2 | [ ] | [ ] | [ ] | [ ] |") == 3
    assert text.count("| 3 | [ ] | [ ] | [ ] | [ ] |") == 3
    assert "does not qualify deck flex" in text

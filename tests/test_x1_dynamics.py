import json

import pytest

from simulation.x1_dynamics import load_mass


def _profile(tmp_path, payload):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_default_mass_is_generic_reference():
    rider, total = load_mass()
    assert rider == pytest.approx(50.0)
    assert total == pytest.approx(70.0)


def test_schema_v2_mass_and_board_mass_are_consumed(tmp_path):
    rider, total = load_mass(_profile(tmp_path, {"schema_version": 2, "mass_kg": 49.9, "board_mass_kg": 17.2}))
    assert rider == pytest.approx(49.9)
    assert total == pytest.approx(67.1)


def test_legacy_rider_mass_is_still_accepted(tmp_path):
    rider, total = load_mass(_profile(tmp_path, {"rider_mass_kg": 51.0}))
    assert rider == pytest.approx(51.0)
    assert total == pytest.approx(71.0)


def test_conflicting_mass_fields_fail_closed(tmp_path):
    path = _profile(tmp_path, {"mass_kg": 49.9, "rider_mass_kg": 55.0})
    with pytest.raises(ValueError, match="conflicts"):
        load_mass(path)


@pytest.mark.parametrize("field", ["mass_kg", "board_mass_kg"])
def test_nonpositive_mass_is_rejected(tmp_path, field):
    path = _profile(tmp_path, {field: 0})
    with pytest.raises(ValueError, match="finite positive mass"):
        load_mass(path)

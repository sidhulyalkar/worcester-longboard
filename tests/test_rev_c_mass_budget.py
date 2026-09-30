import pytest

from simulation.rev_c_mass_budget import custom_budget, reference_budget


def test_trail_reference_budget_exposes_tight_remaining_headroom():
    report = reference_budget("trail").as_dict()
    assert report["target_mass_lb"] == 35.0
    assert report["known_mass_lb"] == 29.6
    assert report["remaining_headroom_lb"] == 5.4
    assert report["target_exceeded_by_known_parts"] is False


def test_range_reference_budget_exposes_remaining_headroom():
    report = reference_budget("range").as_dict()
    assert report["target_mass_lb"] == 45.0
    assert report["known_mass_lb"] == 34.6
    assert report["remaining_headroom_lb"] == 10.4


def test_positive_headroom_is_not_reported_as_feasibility_proof():
    report = reference_budget("trail").as_dict()
    assert "does not prove" in report["interpretation"]


def test_custom_budget_can_show_target_overrun():
    report = custom_budget(20.0, {"a": 12.0, "b": 10.0}).as_dict()
    assert report["target_exceeded_by_known_parts"] is True
    assert report["remaining_headroom_lb"] == -2.0


@pytest.mark.parametrize(
    "target,components",
    [
        (0, {"a": 1.0}),
        (10, {}),
        (10, {"": 1.0}),
        (10, {"a": -1.0}),
    ],
)
def test_invalid_custom_mass_budget_fails_closed(target, components):
    with pytest.raises(ValueError):
        custom_budget(target, components)


def test_warren_reference_budget_is_tighter_but_explicit():
    trail = reference_budget("trail", "pro_warren_iii").as_dict()
    range_case = reference_budget("range", "pro_warren_iii").as_dict()
    assert trail["known_mass_lb"] == 30.9
    assert trail["remaining_headroom_lb"] == 4.1
    assert range_case["known_mass_lb"] == 35.9
    assert range_case["remaining_headroom_lb"] == 9.1


def test_unknown_chassis_reference_is_rejected():
    with pytest.raises(ValueError, match="chassis"):
        reference_budget("trail", "unknown")

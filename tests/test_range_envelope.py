import math

import pytest

from simulation.range_envelope import RangeEnvelope, planning_envelope


def test_1080wh_trail_pack_with_20_percent_reserve_is_conservative():
    report = planning_envelope(1080, "trail", 0.20).as_dict()
    assert report["usable_wh"] == 864.0
    assert report["range_miles"] == [19.2, 27.0]


def test_1080wh_mixed_surface_planning_envelope():
    env = planning_envelope(1080, "mixed", 0.20)
    assert math.isclose(env.conservative_miles, 28.8)
    assert math.isclose(env.optimistic_miles, 864 / 22)


def test_540wh_trail_configuration_keeps_range_expectations_modest():
    env = planning_envelope(540, "trail", 0.20)
    assert env.conservative_miles == pytest.approx(9.6)
    assert env.optimistic_miles == pytest.approx(13.5)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(nominal_wh=0, reserve_fraction=0.2, wh_per_mile_low=20, wh_per_mile_high=30),
        dict(nominal_wh=500, reserve_fraction=1.0, wh_per_mile_low=20, wh_per_mile_high=30),
        dict(nominal_wh=500, reserve_fraction=-0.1, wh_per_mile_low=20, wh_per_mile_high=30),
        dict(nominal_wh=500, reserve_fraction=0.2, wh_per_mile_low=40, wh_per_mile_high=30),
    ],
)
def test_invalid_range_inputs_fail_closed(kwargs):
    with pytest.raises(ValueError):
        RangeEnvelope(**kwargs).validate()


def test_unknown_terrain_rejected():
    with pytest.raises(ValueError, match="unknown terrain"):
        planning_envelope(1000, "moon")

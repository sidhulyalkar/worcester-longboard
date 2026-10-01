import pytest

from simulation.rev_c_energy_planner import (
    MissionPlan,
    cold_swap_inventory_plan,
    ideal_charge_lower_bound,
)


def test_540wh_trail_reference_matches_existing_planning_envelope():
    report = MissionPlan(
        distance_miles=10,
        terrain="trail",
        reserve_fraction=0.20,
        pack_wh=540,
    ).as_dict()
    assert report["pack_range_envelope_miles"] == [9.6, 13.5]
    assert report["packs_needed"]["conservative_consumption_case"] == 2
    assert report["cold_swaps_needed"]["conservative_consumption_case"] == 1


def test_1089wh_range_reference_covers_20_trail_miles_only_in_optimistic_case():
    report = MissionPlan(
        distance_miles=20,
        terrain="trail",
        reserve_fraction=0.20,
        pack_wh=1089,
    ).as_dict()
    assert report["pack_range_envelope_miles"] == [19.4, 27.2]
    assert report["single_pack_covers_optimistic_case"] is True
    assert report["single_pack_covers_conservative_case"] is False


def test_1089wh_mixed_surface_reference_covers_30_miles_only_in_optimistic_case():
    report = MissionPlan(
        distance_miles=30,
        terrain="mixed",
        reserve_fraction=0.20,
        pack_wh=1089,
    ).as_dict()
    assert report["pack_range_envelope_miles"] == [29.0, 39.6]
    assert report["single_pack_covers_optimistic_case"] is True
    assert report["single_pack_covers_conservative_case"] is False


def test_cold_swap_inventory_keeps_only_one_small_pack_installed():
    report = cold_swap_inventory_plan(
        distance_miles=20,
        terrain="trail",
        reserve_fraction=0.20,
        pack_wh=540,
        pack_mass_lb=15,
    )
    assert report["installed_pack_count_at_once"] == 1
    assert report["installed_battery_mass_lb"] == 15
    assert report["inventory"]["conservative_consumption_case"]["pack_count"] == 3
    assert (
        report["inventory"]["conservative_consumption_case"][
            "total_pack_inventory_mass_lb"
        ]
        == 45
    )
    assert (
        report["inventory"]["conservative_consumption_case"]["cold_swaps_needed"]
        == 2
    )
    assert report["hot_swap_assumed"] is False
    assert report["parallel_pack_operation_assumed"] is False
    assert report["powered_operation_authorized"] is False


def test_cold_swap_inventory_rejects_invalid_pack_mass():
    with pytest.raises(ValueError, match="pack_mass_lb"):
        cold_swap_inventory_plan(
            distance_miles=10,
            terrain="mixed",
            reserve_fraction=0.20,
            pack_wh=540,
            pack_mass_lb=0,
        )


def test_charge_time_is_explicitly_only_an_ideal_lower_bound():
    report = ideal_charge_lower_bound(
        pack_wh=1089,
        charger_power_w=1050,
        start_soc_fraction=0.10,
        target_soc_fraction=0.90,
    )
    assert report["energy_added_wh"] == pytest.approx(871.2)
    assert report["ideal_lower_bound_minutes"] == pytest.approx(49.8)
    assert report["actual_charge_time_claimed"] is False
    assert report["compatibility_claimed"] is False
    assert "Actual charging is longer" in report["warning"]


def test_540wh_530w_zero_to_full_ideal_lower_bound_is_about_one_hour():
    report = ideal_charge_lower_bound(pack_wh=540, charger_power_w=530)
    assert report["ideal_lower_bound_minutes"] == pytest.approx(61.1)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(distance_miles=0, terrain="trail", reserve_fraction=0.2, pack_wh=540),
        dict(distance_miles=10, terrain="moon", reserve_fraction=0.2, pack_wh=540),
        dict(distance_miles=10, terrain="trail", reserve_fraction=1.0, pack_wh=540),
        dict(distance_miles=10, terrain="trail", reserve_fraction=0.2, pack_wh=0),
    ],
)
def test_invalid_mission_inputs_fail_closed(kwargs):
    with pytest.raises(ValueError):
        MissionPlan(**kwargs).validate()


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(pack_wh=0, charger_power_w=530),
        dict(pack_wh=540, charger_power_w=0),
        dict(pack_wh=540, charger_power_w=530, start_soc_fraction=-0.1),
        dict(pack_wh=540, charger_power_w=530, target_soc_fraction=1.1),
        dict(
            pack_wh=540,
            charger_power_w=530,
            start_soc_fraction=0.8,
            target_soc_fraction=0.8,
        ),
    ],
)
def test_invalid_charge_bound_inputs_fail_closed(kwargs):
    with pytest.raises(ValueError):
        ideal_charge_lower_bound(**kwargs)

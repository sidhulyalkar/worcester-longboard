import pytest

from simulation.rev_c_topology_traction_sweep import SweepConfig, sweep


def test_uphill_sweep_unloads_front_and_penalizes_front_2wd():
    report = sweep(SweepConfig(), [0.0, 0.10, 0.20, 0.30])
    rows = report["rows"]
    assert report["physical_authority"] is False
    assert all(rows[i + 1]["front_load_fraction"] < rows[i]["front_load_fraction"] for i in range(len(rows) - 1))
    assert all(rows[i + 1]["required_mu_front_2wd"] > rows[i]["required_mu_front_2wd"] for i in range(len(rows) - 1))
    assert rows[-1]["required_mu_front_2wd"] > rows[-1]["required_mu_rear_2wd"]


def test_front_vs_rear_tradeoff_is_dimensionless_cg_driven_not_rider_specific():
    cfg = SweepConfig(total_mass_kg=50.0)
    light = sweep(cfg, [0.20])["rows"][0]
    heavy = sweep(SweepConfig(total_mass_kg=100.0), [0.20])["rows"][0]
    assert light["front_load_fraction"] == heavy["front_load_fraction"]
    assert light["required_mu_front_2wd"] == heavy["required_mu_front_2wd"]
    assert light["required_mu_rear_2wd"] == heavy["required_mu_rear_2wd"]


def test_center_of_mass_height_increases_uphill_front_drive_penalty():
    low = sweep(SweepConfig(cg_height_to_wheelbase=0.40), [0.20])["rows"][0]
    high = sweep(SweepConfig(cg_height_to_wheelbase=0.90), [0.20])["rows"][0]
    assert high["front_load_fraction"] < low["front_load_fraction"]
    assert high["required_mu_front_2wd"] > low["required_mu_front_2wd"]


@pytest.mark.parametrize(
    "cfg",
    [
        SweepConfig(wheelbase_m=0),
        SweepConfig(cg_from_rear_fraction=0),
        SweepConfig(cg_from_rear_fraction=1),
        SweepConfig(cg_height_to_wheelbase=0),
        SweepConfig(rolling_resistance_coeff=0.5),
        SweepConfig(acceleration_mps2=-0.1),
    ],
)
def test_invalid_sweep_inputs_fail_closed(cfg):
    with pytest.raises(ValueError):
        sweep(cfg, [0.1])


def test_negative_grade_rejected():
    with pytest.raises(ValueError):
        sweep(SweepConfig(), [-0.1])

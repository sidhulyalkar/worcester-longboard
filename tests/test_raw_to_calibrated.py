from fit.pressure_calibration import from_known_mass
from fit.raw_log import RawSample
from fit.raw_to_calibrated import convert_samples


def calibration():
    # 1000 raw counts -> 10 kg for every channel.
    return {
        name: from_known_mass(1000.0, 2000.0, 10.0)
        for name in ("left_heel", "left_forefoot", "right_heel", "right_forefoot")
    }


def test_complete_raw_samples_convert_to_relative_time_and_newtons():
    samples = [
        RawSample(1_000_000, (1500, 1500, 1500, 1500), 15, 0.1, True),
        RawSample(1_012_500, (1600, 1400, 1500, 1500), 15, 0.2, True),
    ]
    rows = convert_samples(samples, calibration())
    assert len(rows) == 2
    assert rows[0]["t_s"] == 0.0
    assert abs(rows[1]["t_s"] - 0.0125) < 1e-9
    # 500 counts is half of a 10 kg calibration span.
    assert abs(rows[0]["left_heel_N"] - 5.0 * 9.80665) < 1e-6
    assert rows[1]["left_heel_N"] > rows[1]["left_forefoot_N"]
    assert rows[1]["roll_deg"] == 0.2


def test_partial_force_sample_is_not_smuggled_into_qualified_csv():
    samples = [
        RawSample(1_000_000, (1500, 1500, 1500, None), 7, 0.1, True),
        RawSample(1_012_500, (1500, 1500, 1500, 1500), 15, 0.1, True),
    ]
    rows = convert_samples(samples, calibration())
    assert len(rows) == 1
    assert rows[0]["t_s"] == 0.0


def test_missing_imu_row_is_excluded_by_default():
    samples = [
        RawSample(1_000_000, (1500, 1500, 1500, 1500), 15, None, False),
        RawSample(1_012_500, (1500, 1500, 1500, 1500), 15, 0.0, True),
    ]
    rows = convert_samples(samples, calibration())
    assert len(rows) == 1
    assert rows[0]["t_s"] == 0.0

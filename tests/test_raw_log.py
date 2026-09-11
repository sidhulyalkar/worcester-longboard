import pytest

from fit.raw_log import parse_text, quality_report


HEADER = "t_us,left_heel_raw,left_forefoot_raw,right_heel_raw,right_forefoot_raw,load_valid_mask,roll_deg,imu_ok"


def test_complete_log_reports_full_channel_coverage():
    text = "\n".join([
        "# Worcester X1 Fit Rig v0.3 raw logger",
        "# hx711_sps=80",
        HEADER,
        "1000000,10,20,30,40,15,0.10,1",
        "1012500,11,21,31,41,15,0.11,1",
        "1025000,12,22,32,42,15,0.09,1",
    ])
    report = quality_report(parse_text(text))
    assert report["monotonic_time"] is True
    assert report["complete_force_fraction"] == 1.0
    assert report["channel_valid_fraction"]["right_forefoot"] == 1.0
    assert report["median_dt_ms"] == 12.5
    assert report["warnings"] == []


def test_missing_channel_is_visible_in_mask_and_quality_report():
    text = "\n".join([
        HEADER,
        "1000000,10,20,30,nan,7,0.10,1",
        "1012500,11,21,31,nan,7,0.11,1",
    ])
    report = quality_report(parse_text(text))
    assert report["complete_force_fraction"] == 0.0
    assert report["channel_valid_fraction"]["right_forefoot"] == 0.0
    assert any("four force channels" in w for w in report["warnings"])


def test_mask_cannot_claim_nan_channel_is_valid():
    text = "\n".join([
        HEADER,
        "1000000,10,20,30,nan,15,0.10,1",
    ])
    with pytest.raises(ValueError, match="right_forefoot"):
        parse_text(text)


def test_nonmonotonic_timestamp_is_reported():
    text = "\n".join([
        HEADER,
        "1000000,10,20,30,40,15,0.10,1",
        "999000,11,21,31,41,15,0.11,1",
    ])
    report = quality_report(parse_text(text))
    assert report["monotonic_time"] is False
    assert any("monotonic" in w for w in report["warnings"])

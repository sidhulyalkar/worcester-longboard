import csv
import json
from pathlib import Path

import pytest

from tools.init_rev_c_ride_compliance_session import initialize


def test_initializer_creates_private_compliance_workspace(tmp_path: Path):
    session = tmp_path / "session-01"
    report = initialize(session)

    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authorized"] is False

    manifest = json.loads((session / "ride_compliance_manifest.json").read_text())
    assert manifest["scope"] == "rev_c_unpowered_ride_compliance_trials"
    assert manifest["session_id"] == "session-01"

    for run in manifest["runs"]:
        path = session / run["csv_path"]
        assert path.exists()
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == [
            "time_s",
            "speed_mps",
            "accel_z_mps2",
            "gyro_roll_dps",
            "gyro_yaw_dps",
        ]
        assert len(rows) == 1

    observations = session / "rider_observations.csv"
    with observations.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(manifest["runs"])
    assert {row["run_id"] for row in rows} == {
        run["id"] for run in manifest["runs"]
    }


def test_initializer_refuses_to_overwrite_existing_session(tmp_path: Path):
    session = tmp_path / "session-01"
    session.mkdir()
    marker = session / "keep.txt"
    marker.write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(session)

    assert marker.read_text(encoding="utf-8") == "do not overwrite"

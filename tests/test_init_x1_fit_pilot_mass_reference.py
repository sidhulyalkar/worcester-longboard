import json
from pathlib import Path

import pytest

from tools.init_x1_fit_pilot_mass_reference import initialize


def test_initializer_creates_empty_issue61_record(tmp_path: Path):
    path = tmp_path / "mass_reference.json"
    data = initialize(
        path,
        "MASS-REF-001",
        "2026-10-02T18:00:00-07:00",
    )
    assert path.is_file()
    assert data["scope"] == "x1_fit_pilot_mass_reference_record"
    assert data["issue"] == 61
    assert data["reference_set_id"] == "MASS-REF-001"
    assert data["measured_at_utc"] == "2026-10-02T18:00:00-07:00"
    assert data["masses"] == []
    saved = json.loads(path.read_text())
    assert saved == data
    assert saved["claims"]["powered_operation_authorized"] is False


def test_initializer_refuses_overwrite(tmp_path: Path):
    path = tmp_path / "mass_reference.json"
    path.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        initialize(
            path,
            "MASS-REF-001",
            "2026-10-02T18:00:00-07:00",
        )
    assert path.read_text(encoding="utf-8") == "keep"


def test_initializer_requires_nonempty_identity_fields(tmp_path: Path):
    with pytest.raises(ValueError, match="reference_set_id"):
        initialize(
            tmp_path / "a.json",
            "",
            "2026-10-02T18:00:00-07:00",
        )
    with pytest.raises(ValueError, match="measured_at_utc"):
        initialize(
            tmp_path / "b.json",
            "MASS-REF-001",
            "",
        )

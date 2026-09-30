from pathlib import Path

import pytest

from tools.init_rev_c_chassis_release_session import initialize


def test_initializer_creates_complete_private_workspace(tmp_path: Path):
    session = tmp_path / "rev_c_release"
    manifest = initialize(session)
    assert manifest["physical_authority"] is False
    assert manifest["powered_operation_authorized"] is False

    expected = {
        "deck_comparison.json",
        "topology_trade.json",
        "inert_pack_envelope.json",
        "chassis_release.json",
        "workspace_manifest.json",
    }
    assert expected.issubset({p.name for p in session.iterdir()})
    deck_dir = session / "deck_templates"
    assert (deck_dir / "rev_c_comp95_deck_envelope.svg").exists()
    assert (deck_dir / "rev_c_pro_warren_iii_deck_envelope.svg").exists()
    assert (deck_dir / "rev_c_agent_deck_envelope.svg").exists()


def test_initializer_refuses_to_overwrite_existing_session(tmp_path: Path):
    session = tmp_path / "rev_c_release"
    session.mkdir()
    (session / "notes.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(FileExistsError):
        initialize(session)
    assert (session / "notes.txt").read_text(encoding="utf-8") == "keep me"

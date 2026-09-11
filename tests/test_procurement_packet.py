import json
from pathlib import Path

from tools.render_procurement_packet import render_packet

ROOT = Path(__file__).resolve().parents[1]


def test_public_packet_is_actionable_and_fail_closed():
    plan = json.loads((ROOT / "hardware/build_authority.json").read_text())
    procurement = json.loads((ROOT / "hardware/procurement_manifest.json").read_text())
    text = render_packet(plan, procurement)
    assert "**$120.90**" in text
    assert "LC-3135" in text
    assert "FEELER-GAUGE" in text
    assert "DONOR-COMP95" in text
    assert "BRAKE-V5" in text
    assert "TRUCK-M3-400 | MEASURE_FIRST | fallback blocked" in text
    assert "TIRE-T2-9 | MEASURE_FIRST | MEASURE_FIRST item lacks required_for issue authority" in text
    assert "DRIVE-G1-DUAL | POWER_GATED | POWER_GATED is not authorized" in text
    assert "four-zone duplication: **BLOCKED**" in text
    assert "power ordering: **BLOCKED**" in text
    assert "powered operation: **BLOCKED**" in text

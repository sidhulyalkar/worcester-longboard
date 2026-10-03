import copy
import json
from pathlib import Path

import pytest

from tools.init_x1_physical_kickoff import initialize
from tools.render_physical_kickoff_packet import render

ROOT = Path(__file__).resolve().parents[1]


def _plan():
    return json.loads((ROOT / "hardware/build_authority.json").read_text())


def _procurement():
    return json.loads((ROOT / "hardware/procurement_manifest.json").read_text())


def _inventory():
    return json.loads(
        (ROOT / "hardware/x1_physical_kickoff_inventory_template.json").read_text()
    )


def _item(inventory, item_id):
    return next(row for row in inventory["items"] if row["id"] == item_id)


def test_public_kickoff_keeps_expensive_hardware_blocked():
    text = render(_plan(), _procurement(), _inventory())

    assert "Required exact Issue #4 evidence hardware: **$23.90**" in text
    assert "Optional-if-owned tools/materials ceiling: **$97.00**" in text
    assert "No-inventory worst-case Cart A total: **$120.90**" in text
    assert "Current maximum remaining checkout" in text
    assert "chassis/brake MEASURE_FIRST purchase: **BLOCKED**" in text
    assert "power ordering: **BLOCKED**" in text
    assert "powered operation: **BLOCKED**" in text
    assert "public operation: **BLOCKED**" in text
    assert "dog-accompanied operation: **BLOCKED**" in text
    assert "| DONOR-COMP95 | MEASURE_FIRST | BLOCKED |" in text
    assert "| BATTERY-PRO-MODULAR | POWER_GATED | BLOCKED |" in text


def test_owned_optional_tools_reduce_duplicate_checkout_only():
    inventory = _inventory()
    row = _item(inventory, "MCU-ESP32S3")
    row.update(
        {
            "status": "OWNED_EQUIVALENT",
            "qty_owned_verified": 1,
            "exact_part_match": False,
            "unused_or_known_history": True,
        }
    )
    row = _item(inventory, "CALIPER-SCREENING")
    row.update(
        {
            "status": "OWNED_EQUIVALENT",
            "qty_owned_verified": 1,
            "exact_part_match": False,
            "unused_or_known_history": True,
        }
    )

    text = render(_plan(), _procurement(), inventory)

    assert "VERIFY_OWNED_AND_SKIP_DUPLICATE" in text
    assert "$80.90" in text
    assert "| DONOR-COMP95 | MEASURE_FIRST | BLOCKED |" in text


def test_required_evidence_hardware_needs_exact_known_match_to_skip_purchase():
    inventory = _inventory()
    row = _item(inventory, "LC-3135")
    row.update(
        {
            "status": "OWNED_EQUIVALENT",
            "qty_owned_verified": 2,
            "exact_part_match": False,
            "unused_or_known_history": True,
        }
    )
    text = render(_plan(), _procurement(), inventory)
    assert "| LC-3135 | 2 | Phidgets / 3135_0 | $14.00 | OWNED_EQUIVALENT | ORDER_OR_VERIFY |" in text

    row.update(
        {
            "status": "OWNED_EXACT_UNUSED",
            "exact_part_match": True,
        }
    )
    text = render(_plan(), _procurement(), inventory)
    assert "VERIFY_EXACT_UNUSED_WITH_ISSUE4_GUIDE" in text
    assert "$106.90" in text


def test_inventory_cannot_contain_blocked_or_unknown_item():
    inventory = _inventory()
    inventory["items"].append(
        {
            "id": "DONOR-COMP95",
            "status": "NEED_BUY",
            "qty_owned_verified": 0,
            "exact_part_match": False,
            "unused_or_known_history": False,
            "notes": "",
        }
    )

    with pytest.raises(ValueError, match="current BUY_NOW"):
        render(_plan(), _procurement(), inventory)


def test_renderer_rejects_tampered_attempt_to_open_non_buy_now_item():
    plan = copy.deepcopy(_plan())
    # Artificial regression fixture: remove the chassis gate and item selection
    # constraints. Either the manifest validator or the renderer's redundant
    # no-evidence check must reject this state.
    plan["gates"]["rev_c_chassis_release_qualified"]["requires"] = []
    procurement = copy.deepcopy(_procurement())
    donor = next(x for x in procurement["items"] if x["id"] == "DONOR-COMP95")
    donor.pop("requires_gate", None)
    donor.pop("requires_gate_selections", None)

    with pytest.raises(ValueError) as exc:
        render(plan, procurement, _inventory())
    assert (
        "invalid procurement manifest" in str(exc.value)
        or "unexpectedly open non-BUY_NOW" in str(exc.value)
    )


def test_initializer_creates_full_private_kickoff_workspace(tmp_path: Path):
    workspace = tmp_path / "physical-kickoff"
    report = initialize(workspace)

    assert report["scope"] == "x1_physical_kickoff_workspace"
    assert report["procurement_authority"] is False
    assert report["fabrication_authority"] is False
    assert report["powered_operation_authority"] is False
    assert report["public_operation_authority"] is False
    assert report["dog_accompanied_operation_authority"] is False
    assert report["cart_a_checkout_protocol"] == "docs/x1_cart_a_checkout_receiving.md"
    assert report["cart_a_checkout_template"] == "hardware/x1_cart_a_checkout_template.json"
    assert report["cart_a_receiving_template"] == "hardware/x1_cart_a_receiving_template.json"

    assert (workspace / "owned_inventory.json").is_file()
    assert (workspace / "DAY0_KICKOFF.md").is_file()
    assert (workspace / "NEXT_STEPS.md").is_file()
    assert (workspace / "rev_c_release" / "workspace_manifest.json").is_file()

    deck_dir = workspace / "rev_c_release" / "deck_templates"
    svgs = sorted(deck_dir.glob("*.svg"))
    assert len(svgs) == 3

    packet = (workspace / "DAY0_KICKOFF.md").read_text()
    assert "Required exact Issue #4 evidence hardware: **$23.90**" in packet
    assert "No-inventory worst-case Cart A total: **$120.90**" in packet
    assert "MEASURE_FIRST purchase: **BLOCKED**" in packet

    next_steps = (workspace / "NEXT_STEPS.md").read_text()
    assert "init_x1_cart_a_checkout.py" in next_steps
    assert "x1_cart_a_checkout_receiving.md" in next_steps
    assert "fingerprinted Issue #56 receiving record" in next_steps


def test_initializer_refuses_to_overwrite_private_work(tmp_path: Path):
    workspace = tmp_path / "physical-kickoff"
    workspace.mkdir()
    marker = workspace / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(workspace)

    assert marker.read_text(encoding="utf-8") == "keep"

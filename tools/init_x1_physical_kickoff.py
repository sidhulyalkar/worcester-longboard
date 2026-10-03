#!/usr/bin/env python3
"""Initialize the Worcester X1 Day-0 physical kickoff workspace."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.init_rev_c_chassis_release_session import initialize as init_rev_c_release
from tools.render_physical_kickoff_packet import render

INVENTORY_TEMPLATE = ROOT / "hardware/x1_physical_kickoff_inventory_template.json"
PLAN = ROOT / "hardware/build_authority.json"
PROCUREMENT = ROOT / "hardware/procurement_manifest.json"


def initialize(workspace_dir: Path) -> dict:
    workspace_dir = workspace_dir.resolve()
    if workspace_dir.exists() and any(workspace_dir.iterdir()):
        raise FileExistsError(f"workspace directory is not empty: {workspace_dir}")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = workspace_dir / "owned_inventory.json"
    shutil.copyfile(INVENTORY_TEMPLATE, inventory_path)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    procurement = json.loads(PROCUREMENT.read_text(encoding="utf-8"))
    packet_path = workspace_dir / "DAY0_KICKOFF.md"
    packet_path.write_text(render(plan, procurement, inventory) + "\n", encoding="utf-8")

    release_dir = workspace_dir / "rev_c_release"
    release_manifest = init_rev_c_release(release_dir)

    handoff_lines = [
        "# Worcester X1 physical kickoff handoff",
        "",
        "## Before checkout",
        "",
        "1. Open owned_inventory.json and physically inventory the listed BUY_NOW items.",
        "2. Re-render DAY0_KICKOFF.md after editing the inventory.",
        "3. Use rev_c_release/deck_templates for the zero-cost three-way stance experiment.",
        "4. Initialize and validate an Issue #56 Cart A checkout record before payment.",
        "5. Order only Cart A items still marked for purchase by the validated checkout.",
        "",
        "Render command:",
        "python tools/render_physical_kickoff_packet.py --inventory rider/private/physical_kickoff/owned_inventory.json --out rider/private/physical_kickoff/DAY0_KICKOFF.md",
        "",
        "Checkout initializer:",
        "python tools/init_x1_cart_a_checkout.py rider/private/physical_kickoff/cart_a_checkout.json --inventory rider/private/physical_kickoff/owned_inventory.json --checkout-id CART-A-YYYY-MM-DD-A",
        "",
        "Checkout protocol:",
        "docs/x1_cart_a_checkout_receiving.md",
        "",
        "## After Cart A arrives",
        "",
        "1. Reconcile ordered hardware through the fingerprinted Issue #56 receiving record.",
        "2. Record packaging, SKU, revision, condition, and stable hardware IDs privately.",
        "3. Preserve one load cell and one HX711 as untouched spares.",
        "4. Create and validate the Issue #59 pilot hardware selection authority.",
        "5. Generate one-zone pilot CAD with: python cad/generate_one_zone_pilot.py",
        "6. Follow hardware/one_zone_pilot_assembly.md.",
        "7. Create and validate Issue #61 calibration-mass reference evidence.",
        "8. Initialize tools/init_one_zone_pilot_session.py from both the Issue #59 hardware authority and Issue #61 mass authority.",
        "9. Do not edit mass values/uncertainties or swap to a spare inside the same Issue #4 session; create new evidence and a new session instead.",
        "10. After Issue #4 qualifies, run Issue #63 platform repeatability; do not duplicate four zones until both gates pass.",
        "",
        "## Hard holds",
        "",
        "- no chassis/brake checkout before Issue #25 release;",
        "- no power hardware checkout;",
        "- no live battery used for mechanical discovery;",
        "- no powered riding.",
        "",
    ]
    handoff_path = workspace_dir / "NEXT_STEPS.md"
    handoff_path.write_text("\n".join(handoff_lines), encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "scope": "x1_physical_kickoff_workspace",
        "workspace_dir": str(workspace_dir),
        "inventory": inventory_path.name,
        "day0_packet": packet_path.name,
        "next_steps": handoff_path.name,
        "rev_c_release_workspace": release_dir.name,
        "rev_c_release_scope": release_manifest.get("scope"),
        "cart_a_checkout_protocol": "docs/x1_cart_a_checkout_receiving.md",
        "cart_a_checkout_template": "hardware/x1_cart_a_checkout_template.json",
        "cart_a_receiving_template": "hardware/x1_cart_a_receiving_template.json",
        "fit_pilot_hardware_selection_protocol": "docs/x1_fit_pilot_hardware_provenance.md",
        "fit_pilot_hardware_selection_template": "hardware/x1_fit_pilot_hardware_selection_template.json",
        "fit_pilot_mass_reference_protocol": "docs/x1_fit_pilot_mass_reference.md",
        "fit_pilot_mass_reference_template": "hardware/x1_fit_pilot_mass_reference_template.json",
        "procurement_authority": False,
        "fabrication_authority": False,
        "powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "interpretation_boundary": "This workspace orchestrates existing authority only. It cannot make blocked items orderable or authorize fabrication or operation.",
    }
    manifest_path = workspace_dir / "workspace_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(initialize(args.workspace_dir), indent=2))


if __name__ == "__main__":
    main()

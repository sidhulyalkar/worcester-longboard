from tools.qualify_rev_c_topology_trade import qualify


TOPOLOGIES = (
    "REAR_V5_FRONT_2WD",
    "REAR_V5_REAR_2WD_SHARED",
    "REAR_2WD_FRONT_VENDOR_HYDRAULIC",
    "ALTERNATE_REAR_DRIVE_PRESERVING_V5",
)


def _manifest():
    evaluations = {}
    for topology in TOPOLOGIES:
        evaluations[topology] = {
            "status": "KEEP_LIVE",
            "reason": "retained for comparison",
            "known_catalog_or_safety_blocker": False,
        }
    evaluations["REAR_2WD_FRONT_VENDOR_HYDRAULIC"]["status"] = "SELECTED_FOR_MEASUREMENT"
    evaluations["REAR_2WD_FRONT_VENDOR_HYDRAULIC"]["reason"] = (
        "preserves rear-drive traction with independent vendor-engineered front braking"
    )
    return {
        "schema_version": 1,
        "scope": "rev_c_pre_purchase_topology_trade",
        "selected_topology_for_measurement": "REAR_2WD_FRONT_VENDOR_HYDRAULIC",
        "traction_sweep_record_sha256": "a" * 64,
        "candidate_evaluations": evaluations,
        "checks": {
            "manufacturer_constraints_recorded": True,
            "traction_sweep_reviewed": True,
            "independent_stopping_path_credible": True,
            "front_hydraulic_reference_treated_as_complete_system_not_adapter": True,
            "no_unqualified_safety_critical_adapter": True,
            "physical_measurement_plan_defined": True,
        },
        "powered_operation_authorized": False,
    }


def test_valid_topology_trade_selects_only_measurement_priority():
    report = qualify(_manifest())
    assert report["qualified"] is True
    assert report["authority"] == "x1_rev_c_topology_trade"
    assert (
        report["selected_topology_for_measurement"]
        == "REAR_2WD_FRONT_VENDOR_HYDRAULIC"
    )
    assert report["powered_operation_authorized"] is False


def test_selected_topology_cannot_have_known_safety_blocker():
    data = _manifest()
    data["candidate_evaluations"]["REAR_2WD_FRONT_VENDOR_HYDRAULIC"][
        "known_catalog_or_safety_blocker"
    ] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert any("known catalog or safety blocker" in e for e in report["errors"])


def test_exactly_one_topology_must_be_selected():
    data = _manifest()
    data["candidate_evaluations"]["REAR_V5_REAR_2WD_SHARED"]["status"] = (
        "SELECTED_FOR_MEASUREMENT"
    )
    report = qualify(data)
    assert report["qualified"] is False
    assert any("exactly one topology" in e for e in report["errors"])


def test_all_four_topologies_must_be_explicitly_evaluated():
    data = _manifest()
    del data["candidate_evaluations"]["REAR_V5_FRONT_2WD"]
    report = qualify(data)
    assert report["qualified"] is False
    assert any("missing candidate evaluation" in e for e in report["errors"])


def test_custom_brake_adapter_path_fails_closed():
    data = _manifest()
    data["checks"]["no_unqualified_safety_critical_adapter"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any("no_unqualified_safety_critical_adapter" in e for e in report["errors"])

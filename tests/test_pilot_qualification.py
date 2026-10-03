import csv, hashlib, json
from pathlib import Path
import pytest
from fit.pilot_qualification import qualify_manifest

HEADER=["t_us","left_heel_raw","left_forefoot_raw","right_heel_raw","right_forefoot_raw","load_valid_mask","roll_deg","imu_ok"]


def _digest(data):
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _write_provenance(tmp: Path):
    selection = {
        "schema_version": 1,
        "scope": "x1_fit_pilot_hardware_selection_record",
        "issue": 59,
        "selection_id": "PILOT-HW-TEST",
        "selected_at_utc": "2026-10-03T12:30:00-07:00",
        "checkout_id": "CART-A-TEST",
        "checkout_authority_fingerprint_sha256": "a" * 64,
        "inventory_record_sha256": "b" * 64,
        "receiving_id": "RECEIVE-TEST",
        "receiving_authority_fingerprint_sha256": "c" * 64,
        "hardware": {
            "load_cell": {
                "item_id": "LC-3135",
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": "LC-PILOT-A",
                "spare_hardware_id": "LC-SPARE-A",
            },
            "hx711": {
                "item_id": "ADC-HX711",
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": "ADC-PILOT-A",
                "spare_hardware_id": "ADC-SPARE-A",
            },
            "mcu": {
                "item_id": "MCU-ESP32S3",
                "source_kind": "NOT_USED",
                "active_hardware_id": "",
            },
        },
        "notes": "",
        "physical_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }
    authority = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_hardware_selection",
        "valid": True,
        "errors": [],
        "selection_id": selection["selection_id"],
        "selection_record_sha256": _digest(selection),
        "checkout_id": selection["checkout_id"],
        "checkout_authority_fingerprint_sha256": selection[
            "checkout_authority_fingerprint_sha256"
        ],
        "inventory_record_sha256": selection["inventory_record_sha256"],
        "receiving_id": selection["receiving_id"],
        "receiving_authority_fingerprint_sha256": selection[
            "receiving_authority_fingerprint_sha256"
        ],
        "hardware": selection["hardware"],
        "exact_evidence_hardware_verified": True,
        "untouched_spares_preserved": True,
        "physical_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": "synthetic selection authority",
    }
    authority["authority_fingerprint_sha256"] = _digest(authority)

    provenance = tmp / "provenance"
    provenance.mkdir(exist_ok=True)
    selection_path = provenance / "hardware_selection.json"
    authority_path = provenance / "hardware_selection_authority.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    authority_path.write_text(json.dumps(authority), encoding="utf-8")

    mass_record = {
        "schema_version": 1,
        "scope": "x1_fit_pilot_mass_reference_record",
        "issue": 61,
        "reference_set_id": "MASS-REF-TEST",
        "measured_at_utc": "2026-10-03T13:00:00-07:00",
        "method": "INDEPENDENT_SCALE_MANUFACTURER_SPEC",
        "uncertainty_policy": {
            "max_relative_uncertainty_fraction": 0.005,
            "rationale": "synthetic",
        },
        "instrument": {},
        "masses": [],
        "nist_traceability_claimed": False,
        "commercial_legal_metrology_claimed": False,
        "physical_sensor_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }
    summaries = [
        {
            "mass_id": "M2",
            "role": "CALIBRATION",
            "accepted_mass_kg": 2.0,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.0025,
        },
        {
            "mass_id": "M5",
            "role": "CALIBRATION",
            "accepted_mass_kg": 5.0,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.001,
        },
        {
            "mass_id": "M10",
            "role": "CALIBRATION",
            "accepted_mass_kg": 10.0,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.0005,
        },
        {
            "mass_id": "M7P5",
            "role": "VALIDATION",
            "accepted_mass_kg": 7.5,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.005 / 7.5,
        },
    ]
    mass_authority = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_mass_reference",
        "scope": "issue4_mass_reference_only",
        "valid": True,
        "errors": [],
        "reference_set_id": mass_record["reference_set_id"],
        "mass_reference_record_sha256": _digest(mass_record),
        "method": mass_record["method"],
        "calibration_masses_kg": [2.0, 5.0, 10.0],
        "validation_mass_kg": 7.5,
        "mass_summaries": summaries,
        "max_relative_uncertainty_fraction": 0.0025,
        "nist_traceability_claimed": False,
        "commercial_legal_metrology_claimed": False,
        "physical_sensor_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": "synthetic mass authority",
    }
    mass_authority["authority_fingerprint_sha256"] = _digest(mass_authority)
    (provenance / "mass_reference.json").write_text(
        json.dumps(mass_record), encoding="utf-8"
    )
    (provenance / "mass_reference_authority.json").write_text(
        json.dumps(mass_authority), encoding="utf-8"
    )
    return selection, authority, mass_record, mass_authority


def _write_log(path:Path,mean_raw:float,seconds:float=6.0,sps:int=10,noise:int=2,header_sps:int|None=None):
    n=int(seconds*sps)+1
    with path.open("w",newline="",encoding="utf-8") as f:
        f.write(f"# hx711_sps={header_sps if header_sps is not None else sps}\n")
        w=csv.writer(f); w.writerow(HEADER)
        for i in range(n):
            j=(i%(2*noise+1))-noise if noise else 0
            w.writerow([i*int(1_000_000/sps),int(round(mean_raw+j)),"","","",1,"",0])

def _manifest(tmp:Path,nonlinear_validation=False,loaded_gap=0.30):
    raw=lambda m:100000+m*9.80665*1000
    specs=[("zero_pre",0,"zero_pre.csv",raw(0)),("load_up",2,"up2.csv",raw(2)),("load_up",5,"up5.csv",raw(5)),("load_up",10,"up10.csv",raw(10)),("load_down",5,"down5.csv",raw(5)+25),("load_down",2,"down2.csv",raw(2)+15),("zero_post",0,"zero_post.csv",raw(0)+10)]
    for _,_,fn,r in specs:_write_log(tmp/fn,r)
    _write_log(tmp/"validation.csv",raw(7.5)+(4000 if nonlinear_validation else 0))
    selection, authority, mass_record, mass_authority = _write_provenance(tmp)
    mass_rows = {
        row["mass_id"]: row for row in mass_authority["mass_summaries"]
    }
    data={
        "schema_version":1,
        "hardware_selection":{
            "selection_id":authority["selection_id"],
            "selection_record_sha256":authority["selection_record_sha256"],
            "selection_authority_fingerprint_sha256":authority["authority_fingerprint_sha256"],
            "selection_record_path":"provenance/hardware_selection.json",
            "selection_authority_path":"provenance/hardware_selection_authority.json"
        },
        "mass_reference":{
            "reference_set_id":mass_authority["reference_set_id"],
            "mass_reference_record_sha256":mass_authority["mass_reference_record_sha256"],
            "mass_reference_authority_fingerprint_sha256":mass_authority["authority_fingerprint_sha256"],
            "mass_reference_record_path":"provenance/mass_reference.json",
            "mass_reference_authority_path":"provenance/mass_reference_authority.json",
            "max_relative_uncertainty_fraction":mass_authority["max_relative_uncertainty_fraction"]
        },
        "hardware_ids":{"load_cell_id":"LC-PILOT-A","hx711_id":"ADC-PILOT-A","pod_id":"POD-PILOT-A","zone_pad_id":"PAD-PILOT-A","mcu_id":""},
        "spare_hardware_ids":{"load_cell_id":"LC-SPARE-A","hx711_id":"ADC-SPARE-A"},
        "channel":"left_heel","hx711_sps":10,
        "acquisition":{"rate_jumper_verified":True},
        "observations":[
            {
                "kind":k,
                "mass_kg":m,
                "mass_id":(
                    None if m == 0 else
                    ("M2" if m == 2 else "M5" if m == 5 else "M10")
                ),
                **(
                    {} if m == 0 else {
                        "reference_uncertainty_kg": mass_rows[
                            "M2" if m == 2 else "M5" if m == 5 else "M10"
                        ]["declared_expanded_uncertainty_kg"]
                    }
                ),
                "log":f,
            }
            for k,m,f,_ in specs
        ],
        "validation":[{
            "mass_kg":7.5,
            "mass_id":"M7P5",
            "reference_uncertainty_kg":mass_rows["M7P5"]["declared_expanded_uncertainty_kg"],
            "log":"validation.csv"
        }],
        "mechanical":{"vendor_pattern_verified":True,"fixed_loaded_orientation_verified":True,"screw_stack_verified":True,"stop_gap_unloaded_mm":0.8,"stop_gap_min_loaded_mm":loaded_gap}
    }
    p=tmp/"pilot_manifest.json"; p.write_text(json.dumps(data)); return p

def test_good_pilot_qualifies_and_is_fingerprinted(tmp_path):
    r=qualify_manifest(_manifest(tmp_path))
    assert r["qualified_for_four_zone_duplication"] is True
    assert r["failures"]==[] and r["metrics"]["r2"]>=0.999999
    assert r["hardware_ids"]["load_cell_id"]=="LC-PILOT-A"
    assert len(r["source_fingerprints"])==12
    assert r["hardware_provenance"]["selection_id"]=="PILOT-HW-TEST"
    assert r["hardware_provenance"]["untouched_spares"]["load_cell_id"]=="LC-SPARE-A"
    assert r["hardware_provenance"]["untouched_spares"]["hx711_id"]=="ADC-SPARE-A"
    assert r["mass_reference_provenance"]["reference_set_id"]=="MASS-REF-TEST"
    assert r["mass_reference_provenance"]["max_validation_uncertainty_fraction"] > 0
    assert r["metrics"]["validation_error_with_reference_uncertainty"] >= r["metrics"]["validation_error"]
    assert r["metrics"]["residual_fs_with_reference_uncertainty"] >= r["metrics"]["residual_fs"]
    assert len(r["manifest_sha256"])==64
    assert len(r["qualification_tool_sha256"])==64
    assert len(r["authority_fingerprint_sha256"])==64

def test_independent_validation_error_blocks_duplication(tmp_path):
    r=qualify_manifest(_manifest(tmp_path,nonlinear_validation=True))
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("validation_error" in x for x in r["failures"])

def test_mechanical_stop_clearance_blocks_duplication(tmp_path):
    r=qualify_manifest(_manifest(tmp_path,loaded_gap=0.05))
    assert r["qualified_for_four_zone_duplication"] is False
    assert "loaded stop gap invalid" in r["failures"]

def test_missing_hysteresis_pair_is_rejected(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["observations"]=[x for x in d["observations"] if not(x["kind"]=="load_down" and x["mass_kg"]==2)]
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("paired masses" in x for x in r["failures"])

def test_validation_mass_cannot_reuse_calibration_mass(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["validation"][0]["mass_kg"]=5
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "validation mass must be independent of calibration masses" in r["failures"]

def test_unknown_hx711_rate_blocks_duplication(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["hx711_sps"]=42
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "hx711_sps must be 10 or 80" in r["failures"]

def test_logger_header_must_match_manifest_rate(tmp_path):
    p=_manifest(tmp_path); raw=lambda m:100000+m*9.80665*1000
    _write_log(tmp_path/"validation.csv",raw(7.5),header_sps=80)
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("logger hx711_sps disagrees" in x for x in r["failures"])

def test_rate_jumper_verification_is_explicit(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["acquisition"]["rate_jumper_verified"]=False
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "acquisition.rate_jumper_verified must be true" in r["failures"]

def test_pilot_mass_ceiling_blocks_needlessly_large_load(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["validation"][0]["mass_kg"]=21.0
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("hard 20 kg" in x for x in r["failures"])

def test_manifest_cannot_escape_private_session_root(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    outside=tmp_path.parent/"outside.csv"; _write_log(outside,100000)
    d["observations"][0]["log"]="../outside.csv"; p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="escapes manifest directory"): qualify_manifest(p)

def test_hardware_identity_is_required(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["hardware_ids"]["load_cell_id"]=""
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "hardware_ids.load_cell_id must be a nonempty string" in r["failures"]

def test_manifest_cannot_swap_selected_active_sensor_id(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["hardware_ids"]["load_cell_id"]="LC-SPARE-A"
    p.write_text(json.dumps(d))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("does not match selected active load cell" in x for x in r["failures"])


def test_tampered_selection_record_blocks_pilot_even_with_good_sensor_metrics(tmp_path):
    p=_manifest(tmp_path)
    selection_path=tmp_path/"provenance"/"hardware_selection.json"
    selection=json.loads(selection_path.read_text())
    selection["hardware"]["load_cell"]["active_hardware_id"]="LC-TAMPERED"
    selection_path.write_text(json.dumps(selection))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("does not match copied selection record" in x for x in r["failures"])


def test_manifest_cannot_hide_untouched_spare_lineage(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["spare_hardware_ids"]["hx711_id"]="ADC-PILOT-A"
    p.write_text(json.dumps(d))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("HX711 spare does not match selected untouched spare" in x for x in r["failures"])


def test_tampered_mass_reference_record_blocks_good_sensor_metrics(tmp_path):
    p=_manifest(tmp_path)
    path=tmp_path/"provenance"/"mass_reference.json"
    data=json.loads(path.read_text())
    data["reference_set_id"]="TAMPERED"
    path.write_text(json.dumps(data))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("does not match copied record" in x for x in r["failures"])


def test_manifest_cannot_change_reference_mass_or_uncertainty(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    up=next(x for x in d["observations"] if x.get("mass_id")=="M5" and x["kind"]=="load_up")
    up["mass_kg"]=5.1
    up["reference_uncertainty_kg"]=0.001
    p.write_text(json.dumps(d))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("mass differs from mass-reference authority" in x for x in r["failures"])
    assert any("uncertainty differs from mass-reference authority" in x for x in r["failures"])


def test_reference_uncertainty_consumes_validation_error_budget(tmp_path):
    p=_manifest(tmp_path)
    authority_path=tmp_path/"provenance"/"mass_reference_authority.json"
    authority=json.loads(authority_path.read_text())
    for row in authority["mass_summaries"]:
        if row["role"]=="VALIDATION":
            row["declared_expanded_uncertainty_kg"]=0.0375
            row["relative_uncertainty_fraction"]=0.005
    authority["max_relative_uncertainty_fraction"]=0.005
    authority.pop("authority_fingerprint_sha256")
    authority["authority_fingerprint_sha256"]=_digest(authority)
    authority_path.write_text(json.dumps(authority))

    record_path=tmp_path/"provenance"/"mass_reference.json"
    record=json.loads(record_path.read_text())
    authority["mass_reference_record_sha256"]=_digest(record)
    authority.pop("authority_fingerprint_sha256")
    authority["authority_fingerprint_sha256"]=_digest(authority)
    authority_path.write_text(json.dumps(authority))

    d=json.loads(p.read_text())
    d["mass_reference"]["mass_reference_authority_fingerprint_sha256"]=authority["authority_fingerprint_sha256"]
    d["mass_reference"]["max_relative_uncertainty_fraction"]=0.005
    d["validation"][0]["reference_uncertainty_kg"]=0.0375
    p.write_text(json.dumps(d))

    # Add roughly 1.7% validation bias. Raw error stays below 2%, but +0.5%
    # reference uncertainty must exceed the canonical 2% combined gate.
    raw=lambda m:100000+m*9.80665*1000
    _write_log(tmp_path/"validation.csv",raw(7.5)+1250)
    r=qualify_manifest(p)
    assert r["metrics"]["validation_error"] < 0.02
    assert r["metrics"]["validation_error_with_reference_uncertainty"] > 0.02
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("validation_error_with_reference_uncertainty above limit" in x for x in r["failures"])


def test_load_sequence_must_be_monotonic(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    ups=[x for x in d["observations"] if x["kind"]=="load_up"]
    ups[0]["mass_kg"],ups[1]["mass_kg"]=ups[1]["mass_kg"],ups[0]["mass_kg"]
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "load_up masses must be strictly ascending" in r["failures"]

def test_thresholds_may_tighten_but_not_relax(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["thresholds"]={"max_validation_error":0.50}
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "threshold max_validation_error may only be made stricter" in r["failures"]

"""Receiving history conflicts, general-document references and authority locks."""
import copy
import json
from pathlib import Path
from configurator.platform_engine import generate_board_design_space,load_platform_bundle
from configurator.build_passport import build_build_passport,propose_passport_revision_change
from configurator.evidence_notebook import empty_evidence_notebook,record_evidence
from configurator.receiving_reconciliation import build_receiving_reconciliation
import pytest

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=load_platform_bundle()
PROFILE=json.loads((ROOT/"configurator/examples/trail_rider_profile.json").read_text())
DOCS=json.loads((ROOT/"catalog/manufacturer_document_references.v1.json").read_text())
CANDIDATES={x["id"]:x for x in generate_board_design_space(PROFILE,BUNDLE)["candidates"]}


def passport(id="brake_first_trail_core"):
    return build_build_passport(CANDIDATES[id],BUNDLE)


def receiving(p,n,rev="R1",qty=1):
    return record_evidence(n,p,{"kind":"RECEIVING_OBSERVATION","component_id":"DONOR-COMP95",
                                "observed_revision":rev,"quantity_received":qty,"as_of":"2026-10-10"})


def test_no_observations_cannot_become_verified_inventory():
    p=passport()
    report=build_receiving_reconciliation(p,empty_evidence_notebook(p),DOCS)
    assert len(report["review_queue"]["no_receiving_observation_ids"])==len(p["parts"])
    donor=next(x for x in report["rows"] if x["component_id"]=="DONOR-COMP95")
    assert donor["actual_assembly_quantity"] is None
    assert donor["actual_supplier_order_quantity"] is None
    assert donor["donor_content_evidence_status"]=="UNVERIFIED_DONOR_CONTENTS"
    assert report["confirmation"]["physical_qualification"]=="NOT_QUALIFIED"
    assert not any(report["authority"].values())


def test_public_mbs_docs_are_leads_only():
    p=passport()
    report=build_receiving_reconciliation(p,empty_evidence_notebook(p),DOCS)
    donor=next(x for x in report["rows"] if x["component_id"]=="DONOR-COMP95")
    assert any(x["url"]=="https://www.mbs.com/manuals" for x in donor["manufacturer_reference_documents"])
    assert any(x["id"]=="mbs-comp95-product" for x in donor["manufacturer_reference_documents"])
    assert all(not x["exact_revision_verified"] for x in donor["manufacturer_reference_documents"])
    assert not donor["revision_matched_manufacturer_manual_verified"]


def test_receiving_observations_do_not_qualify_subparts():
    p=passport()
    n=receiving(p,empty_evidence_notebook(p))
    report=build_receiving_reconciliation(p,n,DOCS)
    donor=next(x for x in report["rows"] if x["component_id"]=="DONOR-COMP95")
    assert donor["last_observation"]["quantity_received"]==1
    assert donor["receipt_history_status"]=="SELF_REPORTED_RECEIPT_NEEDS_INDEPENDENT_REVIEW"
    assert not donor["physical_revision_verified"]
    assert donor["actual_assembly_quantity"] is None
    assert report["confirmation"]["received_contents_qualified"]==0
    assert not any(report["authority"].values())


def test_conflicting_revisions_or_counts_need_manual_review():
    p=passport()
    n=receiving(p,empty_evidence_notebook(p))
    n=receiving(p,n,"R2",2)
    report=build_receiving_reconciliation(p,n,DOCS)
    donor=next(x for x in report["rows"] if x["component_id"]=="DONOR-COMP95")
    assert donor["last_observation"]["quantity_received"]==2
    assert donor["recorded_receiving_count"]==2
    assert donor["receipt_history_status"]=="CONFLICTING_RECEIPT_HISTORY_REVIEW"
    assert report["review_queue"]["conflicting_receipt_history_ids"]==["DONOR-COMP95"]
    assert not donor["received_inventory_verified"]


def test_stale_forged_book_rejected_by_replay():
    p=passport()
    note=receiving(p,empty_evidence_notebook(p))
    forged=copy.deepcopy(note)
    forged["records"][0]["usable_for_qualification"]=True
    forged["authority"]["procurement_authorized"]=True
    report=build_receiving_reconciliation(p,forged,DOCS)
    assert report["evidence_record_count"]==1
    assert not any(report["authority"].values())
    revised=propose_passport_revision_change(p,"DONOR-COMP95","R2")
    stale=build_receiving_reconciliation(revised,note,DOCS)
    assert stale["evidence_record_count"]==0
    assert stale["confirmation"]["order_lines_qualified"]==0


def test_doc_catalog_rejects_false_applicability_and_non_https():
    p=passport()
    d=copy.deepcopy(DOCS)
    d["entries"][0]["exact_revision_verified"]=True
    with pytest.raises(ValueError,match="Invalid or duplicate"):
        build_receiving_reconciliation(p,None,d)
    d["entries"][0]["exact_revision_verified"]=False
    d["entries"][0]["url"]="javascript:alert(1)"
    with pytest.raises(ValueError,match="Invalid or duplicate"):
        build_receiving_reconciliation(p,None,d)

# Build Passport v1.4: revision-bound evidence notebook

**Status:** user-entered source/receiving/measurement notes only. Not an engineering review, vendor verification, purchase release, assembly instruction set or physical qualification.

This tranche gives the Build Passport an auditable way to collect observations during supplier research and parts receiving while continuing to fail closed on missing physical evidence.

## Snapshot ownership

Each evidence notebook is keyed to the complete Build Passport `candidate_id` + `study_identity_key`. A per-part receipt additionally records the immutable `variant_identity_key` from the exact current catalog snapshot (catalog ID, SKU text, catalog revision, source snapshot identifier, and source date). The notebook is stored **in the local browser only**, not uploaded. The user can export JSON containing the passport, receipt ledger and review queue.

A saved notebook is not automatically transferred to a new BOM, source date, supplier snapshot or proposed revision. Restoring a mismatched or forged notebook returns a fresh empty ledger, and every saved entry is revalidated and reconstructed. Old evidence can still be found in a previously exported file but cannot become current evidence without a new review. A future explicit migration UI can present old notes alongside the changed snapshot without auto-acceptance.

No account credentials, attached photographs, payment details or private files are requested. Users may keep photos locally and add only a note/reference. Avoid entering personal details into evidence notes. No browser upload or external telemetry is added.

## Four receipt categories

| Category | Mandatory self-reported input | Permission granted |
|---|---|---|
| `SOURCE_REFERENCE` | HTTPS reference and as-of date | **None**. Stock and prices remain unconfirmed |
| `RECEIVING_OBSERVATION` | Marked physical revision, received count (1–500) and observed date | **None**. Received count is not design or purchase quantity |
| `MANUFACTURER_INSTRUCTIONS_CANDIDATE` | Candidate HTTPS manual, marked exact revision and date | **None**. A link is not independently verified as a genuine, applicable manufacturer manual |
| `INTERFACE_MEASUREMENT_NOTE` | Catalog interface ID and a written unresolved dimensional question | **None**. A note is not a measured/inspected clearance |

The browser validates bounded lengths, calendar dates, IDs belonging to the selected passport, numeric received counts and HTTPS links without embedded credentials. User-supplied notes and links are HTML-escaped when displayed. `review_status=USER_RECORDED_NOT_INDEPENDENTLY_VERIFIED` and `usable_for_qualification=false` are regenerated, not trusted from an imported/local JSON file.

## Review queue

The evaluator reports which components have user-recorded receiving observations, which have source/manual candidate pointers, which interface claims have notes and which pairwise claims must be revisited if a receiving record introduces an exact revision. Because a bundled donor board could conceal subcomponent changes, any donor receiving revision **conservatively invalidates all pairwise interface claims**. Other received-component revisions invalidate every directly connected claim.

The original `UNKNOWN` or `MEASURE_FIRST` interface findings stay unresolved. Neither a manual candidate nor a measurement note clears them.

The following values remain invariant across all notebook records:

- `manufacturer_manuals_independently_verified=0`
- `assembly_quantities_authorized=0`
- `stock_confirmed=0`
- `physical_qualification=NOT_QUALIFIED`
- All procurement, fabrication, charging and powered-operation authority false.

Independent mechanical, braking, battery, BMS, charger and electrical work is still tracked by the existing physical qualification program.

## Reproduce

```bash
node --test tests/js/test_board_evidence_notebook.mjs
python -m pytest -q tests/test_board_evidence_notebook.py
python tools/compare_evidence_notebooks.py
python tools/serve_board_platform.py
```

Open `http://127.0.0.1:8000/builder/`, select a board, scroll to **Build Passport**, expand **Evidence notebook**, add a typed observation, and export the combined passport/evidence file.

The cross-runtime fixture creates synthetic notes against two actual generated candidate designs and compares complete Python and JavaScript JSON outputs. CI also runs tests for forged review/authority, stale source identity, invalid dates/links, missing variants and donor-transitive invalidation.

## Remaining milestones

1. Find exact-revision original maker manuals and document provenance independently. A storefront listing is not an installation manual.
2. Normalize donor inclusion graphs and actual order/assembly quantities; avoid double-counting contained wheels/hubs and piecemeal replacements.
3. Derive engineering tolerances from measured mounting, axle, brake, wheel and retention geometry, not from text notes.
4. Add a separate human-reviewed import/migration workflow with explicit source/candidate acceptance and role separation.
5. Run manual visual/keyboard/print QA and field receiving pilots against a physically selected board under the separate physical qualification authority.

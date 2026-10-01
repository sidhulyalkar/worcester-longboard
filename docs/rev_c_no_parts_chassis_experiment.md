# Rev-C no-parts chassis experiment

**Purpose:** collect the highest-value rider/chassis evidence possible before any chassis, brake, drivetrain, or battery purchase.

This experiment is static, unpowered, and intentionally low-energy.

It can select a **deck envelope preference** for Issue #25. It cannot qualify deck flex, braking, drivetrain fit, structural strength, or powered riding.

## What you need

- painter's tape, cardboard, foam board, or paper;
- measuring tape or ruler;
- the shoes you expect to ride in;
- a flat floor with clear space around all sides;
- optional phone camera for private reference.

No board hardware is required.

## 1. Initialize the private session

From the repository root:

```bash
python tools/init_rev_c_chassis_release_session.py \
  rider/private/rev_c_release
```

The generated deck templates are:

- `rev_c_comp95_deck_envelope.svg`: 950 x 251 mm;
- `rev_c_pro_warren_iii_deck_envelope.svg`: 980 x 244 mm;
- `rev_c_agent_deck_envelope.svg`: 1020 x 284 mm.

These rectangles represent published **maximum deck envelopes**, not exact outlines.

If printing at full scale is inconvenient, reproduce each rectangle on the floor with painter's tape and mark the centerline.

## 2. Blind the candidate names if practical

To reduce expectation bias, label the floor templates A/B/C without looking at which product each corresponds to during the first pass.

Keep the candidate mapping in a separate note.

Do not change dimensions.

## 3. Perform three independent remounts per envelope

For each trial:

1. stand fully outside the template;
2. reset your posture and look away from prior foot marks;
3. step naturally into a riding stance;
4. mark each shoe outline or record its center/yaw privately;
5. bend into a comfortable low carve posture;
6. shift heel-to-toe as though initiating gentle linked turns;
7. practice stepping off quickly to **both** sides;
8. fully leave the template before the next trial.

Do not deliberately reproduce the previous stance.

## 4. Record geometry privately

Useful private measurements include:

- left and right foot-center position relative to deck center;
- left and right yaw angle;
- center-to-center stance width;
- toe overhang;
- heel overhang;
- minimum distance from either shoe to the side edge;
- front/rear reserve length;
- whether a deep-knee posture forces either shoe into an awkward angle.

Exact measurements stay under `rider/private/`.

The public authority records only sanitized pass/fail outcomes and the selected candidate ID.

## 5. Use five acceptance questions

For each envelope answer:

- Can I get meaningful heel/toe leverage without feeling that I must exaggerate ankle motion?
- Can I enter a deep-knee carving posture without the deck forcing my feet into a bad position?
- Can I step off naturally to either side?
- Do three independent remounts converge to roughly the same useful region?
- Does the stance feel comfortable enough that I would want to hold it for a long trail ride?

Only a candidate with all five accepted can be selected.

## 6. What this experiment isolates

### Comp 95 class

Tests the compact 950 x 251 mm PowerLam geometry baseline.

A favorable result says the wider composite alternatives are not necessary for static leverage.

It says nothing yet about whether medium PowerLam ride feel is preferable on rough ground.

### Pro Warren III class

Tests the narrowest envelope, 980 x 244 mm, while preserving a snowboard-composite chassis hypothesis.

The real board also offers a published 910-970 mm wheelbase range centered on the Comp 95's 940 mm reference.

A favorable static result makes Warren worth preserving for later ride-feel testing.

It does **not** validate its stiff/high-pop flex for trail comfort.

### Agent class

Tests the large 1020 x 284 mm deck.

MBS describes the wide Agent deck as providing extra leverage and suitability for larger riders/feet. The purpose here is to determine whether that extra platform is useful or excessive for this rider rather than assuming wider is better.

Its electric-native ecosystem is irrelevant to this static stance test.

## 7. Enter the session result

Edit:

```
rider/private/rev_c_release/deck_comparison.json
```

For every trial, mark the four required checks only after actually doing them.

For each candidate, set the five summary checks based on the completed trials.

Set:

```
selected_candidate_id
selection_reason
rejected_candidates
```

Every non-selected candidate needs a concrete rejection reason.

## 8. Produce the sanitized authority

Run:

```bash
python tools/qualify_rev_c_deck_comparison.py \
  rider/private/rev_c_release/deck_comparison.json \
  --out rider/private/rev_c_release/deck_comparison_authority.json
```

A successful result contains:

```
"authority": "x1_rev_c_deck_comparison"
"qualified": true
"powered_operation_authorized": false
```

## 9. Do not over-interpret the winner

The envelope comparison answers **fit geometry**, not full chassis quality.

After this experiment:

- Comp still needs real trail-compliance evidence;
- Warren still needs real stiff/high-pop ride-feel evidence;
- Agent still needs missing complete-mass, wheelbase, and brake-interface evidence;
- all candidates still need the topology and inert-pack parts of Issue #25.

The purpose of the experiment is to delete bad geometry early, not crown a finished board.

## 10. Strong stop conditions

Stop and mark the candidate unsuitable for the current rider-interface direction if:

- bilateral emergency step-off is awkward;
- a natural stance repeatedly lies outside the usable envelope;
- heel/toe leverage requires uncomfortable joint positions;
- deep-knee posture creates an obvious edge/foot conflict;
- the candidate only works when you consciously force a stance that is not repeatable.

Do not solve an obviously bad envelope by committing to permanent drilling before the Rev-B rider-fit process.

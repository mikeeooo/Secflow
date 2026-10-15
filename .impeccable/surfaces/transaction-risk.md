# Transaction risk surface

Status: shipped additive risk-explanation extension in the incumbent Romanian white and blue workspace. User-facing title: Detaliile tranzacției. No approved image comp or quality card. The context engine remains unavailable; no detector ran in this pass. The fresh final reviewer returned SHIP with no material findings and confirmed all six risk captures valid.

## Purpose
Explain why a transfer has its current 0–100 risk score, including high-risk and low-risk evidence, while preserving the decision and risk recorded at receipt.

## Composition
1. The header identifies payer, amount/currency, and simulation date. Înapoi la tranzacții returns to the list.
2. De ce acest risc? is the wide primary left panel and the first section in DOM order. It shows Scor actual, explicit Scăzut/Moderat/Ridicat status, a semantic meter, and a concise concrete summary.
3. Indicatori de risc highlights up to three concrete drivers, with descriptions and point contributions. Elemente favorabile highlights up to three relevant favorable observations. Groups appear only when populated.
4. Toți factorii și contribuțiile is closed by default. It contains every stored factor, its contribution and maximum, the summed points, rounded score, and relevant thresholds.
5. A narrower Tranzacția panel shows named sender/recipient, amount, Decizie inițială, and the case action when a case exists.
6. Istoricul cererii și datele sursă is closed by default, holding Risc inițial and original request/device metadata.

## States and behavior
- The score is the rounded sum of stored additive contributions. Evidence covers transaction pattern, amount relative to own history, frequency, device familiarity, failed logins, beneficiary familiarity, recent incoming requests, and available history.
- Favorable facts may contribute few points or zero; they do not subtract points or guarantee safety. Concrete behavioral drivers take priority in the highlighted risk list.
- Current thresholds distinguish review from 45, high risk from 60, and blocking of a new request from 70. The explicit risk status is not the original decision.
- A queued/running request shows automatic-processing feedback. Failed analysis has an error message. If stored explanation is absent, an existing assessment falls back to concise observations; otherwise show evaluating/reference context.
- At 1100px the detail evidence stacks inside the still-two-column layout. At 760px panels stack risk-first, evidence becomes one column, and the score reduces from 40px to 36px. DOM reading order matches visual order.
- Transaction and alert lists label Scor actual and Decizie inițială separately; Vezi cauzele opens this surface. The customer list instead links its latest evaluated outgoing transfer's score to the profile risk context.

## Authority and verification
Implementation: templates/detail.html, templates/risk_explanation.html, templates/transactions.html, templates/dashboard_panels.html, core/views.py, and static/app.css. Semantics: detection/risk.py and stored assessment/transaction explanations. System: DESIGN.md and .impeccable/design.json. Valid final captures: .impeccable/review/risk-desktop-high.jpg, risk-mobile-high.jpg, risk-desktop-low.jpg, and risk-desktop-breakdown.jpg. The two profile captures complete the six validated images. This pass checked source consistency; it did not run a detector or backend tests.

## Content guardrails
Keep the current score, original decision, and historical initial risk distinct. Show concrete facts for both raised and low risk. No algorithm names, raw model scores, or formulas appear in the analyst UI. Scores explain the demonstration data and are not calibrated fraud probabilities. Profile-only alert-volume forecasting remains a separate quantity.

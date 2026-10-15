# Customer profile surface

Status: shipped risk-explanation extension within the incumbent Romanian white and blue workspace. The heading is the fictional customer name; route: /accounts/<id>/. No approved image comp or quality card. The context engine remains unavailable; no detector ran in this pass. The fresh final reviewer returned SHIP with no material findings and confirmed all six risk captures valid.

## Purpose
Investigate a customer's latest evaluated outgoing transfer, its causes, transaction/case history, and restrictions. The separate next-hour alert-volume estimate is computed only after opening this profile.

## Composition
1. Name, public account identifier, current restriction state, and Client fictiv identify the customer. Înapoi la clienți returns to the list.
2. Three summary columns show sent/received requests, Ultimul transfer evaluat, and closed case count. Risk refers to the latest evaluated visible outgoing transfer, never a lifetime maximum.
3. De ce acest risc? precedes the forecast. It identifies that transfer's simulation date and amount, links to its transaction, and reuses the current score/status/meter, concrete risk facts, favorable facts, and contribution disclosure.
4. Estimarea alertelor · următoarea oră remains separate: an approximate alert count and six historical hourly bars plus one next-hour bar. It estimates volume, not fraud probability.
5. Transaction and case histories retain simulated dates, named parties, amounts/decisions, case outcomes, and demonstrative-history labels.
6. Gestionează restricția contului and Detalii sursă și dispozitive remain closed disclosures. Restriction changes require a reason; previously refused transactions remain blocked.

## States and behavior
- No evaluated outgoing transfer: show a dash in the summary and omit the risk explanation panel. The customer list states Fără cereri evaluate.
- Customer-list scores link to #risk-context with Vezi cauzele. The profile links to the specific evaluated transaction.
- Risk and favorable fact groups appear only when populated. The full stored factors and point rounding are secondary details.
- With recent observations, show the profile-only estimate and the last-six-hour request/alert counts. Without recent observations, omit the count/chart and explain the lack of a relevant estimate.
- At 760px risk evidence and the forecast panel stack; risk numbers become 36px, the seven forecast bars remain, and tables scroll. The three profile summary columns remain visible.
- Lists never show or compute per-customer forecasts. Dashboard time-series values are observed aggregate activity, distinct from this estimate.

## Authority and verification
Implementation: templates/account.html, templates/accounts.html, templates/risk_explanation.html, core/views.py, and static/app.css. Semantics: detection/risk.py and stored explanations. System: DESIGN.md and .impeccable/design.json. Valid final captures: .impeccable/review/risk-desktop-profile.jpg and risk-mobile-profile.jpg. This pass verified source consistency without changing implementation.

## Content guardrails
Keep fictional identity, MDL demo, and simulation dates explicit. Label risk as belonging to the latest evaluated transfer; do not imply lifetime or predicted customer fraud risk. Preserve the distinction between current score, original decision, and forecast volume. Algorithm names, raw model scores, and diagnostics stay outside the analyst UI.

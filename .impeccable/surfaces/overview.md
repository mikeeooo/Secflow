# Overview surface

Status: implemented directly in code, following BLUEPRINT.md and the user-approved minimalist blue and white analyst workspace. No approved image comp. Launcher unavailable; this record is derived from source, not a launcher review.

## Purpose
Help an analyst see the scope of simulated payments, identify unresolved investigations, and open a case. The user-facing page title is Overview; it is the blueprint's Dashboard surface.

## Composition
1. Shared sidebar and top bar establish location and signed-in role.
2. Heading and supporting sentence sit beside Print report and Export transactions.
3. Demo workspace notice identifies PaySim plus generated scenarios and the current analysis.
4. Four flat summary metrics show transfers, awaiting review, restricted accounts, and allowed transfers.
5. A wider transfer-activity chart sits beside workspace coverage and amounts separated by currency unit.
6. Needs attention lists open investigations ordered by initial risk, with direct Investigate links.
7. Simulated decision impact reports blocked fraudulent value, allowed fraudulent value, and legitimate transfers blocked, separated by currency.

## States and behavior
- Missing analysis is labeled Awaiting analysis.
- Empty activity invites importing the demo dataset.
- Empty investigations explain that analysis is required to evaluate imported transfers.
- Decisions retain text in addition to badge color; risk is shown out of 100.
- Chart bars have visible values, day labels, tooltips, and a chart label.
- At 760px the chart/coverage split becomes one column and metrics use two columns. Tables scroll horizontally with a visible hint. Actions wrap and navigation becomes horizontal.
- Print hides application chrome and controls. Export links to the transaction CSV endpoint.

## Authority and verification
Visual tokens and reusable components: DESIGN.md and .impeccable/design.json. Implementation: static/app.css, templates/base.html, templates/dashboard.html. Source consistency was checked after independent review fixes. This documentation pass does not claim screenshot comparison or launcher-based validation.

## Content guardrails
Keep simulated timestamp/security provenance visible. Keep source and currency distinctions. Ground truth is used only for retrospective impact evaluation. Review is not counted as prevented loss. Risk scores are not fraud probabilities.

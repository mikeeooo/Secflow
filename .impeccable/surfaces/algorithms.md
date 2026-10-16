# Algorithms surface

Status: shipped Apple-inspired Romanian white and blue redesign. Rezultate de detecție; navigation: Rezultate; route: /algorithms/. User-selected direction and direct code build. The final visual reviewer cleared desktop 1440px, user-width 799px, and phone 390/375px; all 48 application tests passed in the implementation handoff. This documentation pass changes no implementation.

## Purpose
Show a concise combined evaluation of the prepared synthetic test history. The analyst sees outcomes without algorithm names, individual diagnostics, execution controls, or configuration.

## Composition
1. A heading and short subtitle explain identification of suspicious demonstration scenarios. Exportă rezultate appears when a stored run exists.
2. Rezultate pe datele de test states the number of synthetic transfers evaluated separately from reference and validation.
3. Three metrics show Alarme corecte, Fraude detectate, and Alarme false. Each has a plain-language denominator below its percentage.
4. Vezi distribuția rezultatelor is a closed disclosure containing Fraude găsite, Fraude omise, Alarme false, and Legitime nesemnalate in a two-column count grid.
5. A visible caption explains that evaluation scope is explicit: for MIA, the original 768-request historical test stays separate from the played stream. Synthetic percentages do not describe bank performance.

## States and behavior
- With no combined test result, Analiză în pregătire explains that results appear after preparing the demonstration data.
- At 620px the three metrics stack with 26px gaps and 36px values; the disclosed count grid becomes one column. Each metric has a meter and an explicit denominator.
- The page has no source selector, comparison table, validation disclosure, benchmark disclosure, or algorithm run/parameter/import controls.
- For MIA, the original historical-test artifact supplies the displayed combined statistics. If unavailable or version-incompatible, the page labels the latest visible-history replay scope. Playback does not silently rewrite the original test.
- Metric export separates historical_test from latest_visible_replay when the original MIA artifact is available.

## Authority and verification

Current implementation: templates/algorithms.html, core/views.py, artifacts/mia-continuous-evaluation.json, and static/app.css. Reusable tokens and components: DESIGN.md and .impeccable/design.json. The handoff reports completed visual review and 48 passing tests; this pass checked documentation consistency, JSON, and whitespace without rerunning browser review.

## Content guardrails
Keep combined synthetic-test results distinct from the live playback stream. Explain denominators and synthetic-data limits. Do not display algorithm names, raw model scores, theory, parameters, or diagnostics anywhere in the analyst interface. Algorithm theory remains in docs/ALGORITHMS.md; forecasts remain profile-only.

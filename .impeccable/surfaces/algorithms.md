# Algorithms surface

Status: shipped refinement of the incumbent Romanian white and blue workspace. User-facing title: Rezultate de detecție; navigation label: Rezultate; route: /algorithms/. No approved image comp or quality card. Context loader and detector remain unavailable because the bundled engine is missing. The current risk extension received SHIP with no material findings. This record distinguishes the original historical test from local replay statistics.

## Purpose
Show a concise combined evaluation of the prepared synthetic test history. The analyst sees outcomes without algorithm names, individual diagnostics, execution controls, or configuration.

## Composition
1. A heading and short subtitle explain identification of suspicious demonstration scenarios. Exportă rezultate appears when a stored run exists.
2. Rezultate pe datele de test states the number of synthetic transfers evaluated separately from reference and validation.
3. Three metrics show Alarme corecte, Fraude detectate, and Alarme false. Each has a plain-language denominator below its percentage.
4. A wrapping count row shows Fraude găsite, Fraude omise, Alarme false, and Legitime nesemnalate.
5. A visible caption explains that evaluation scope is explicit: for MIA, the original 768-request historical test stays separate from the played stream. Synthetic percentages do not describe bank performance.

## States and behavior
- With no combined test result, Analiză în pregătire explains that results appear after preparing the demonstration data.
- At 760px the three metrics stack vertically with 22px gaps and 30px values. Counts wrap naturally.
- The page has no source selector, comparison table, validation disclosure, benchmark disclosure, or algorithm run/parameter/import controls.
- For MIA, the original historical-test artifact supplies the displayed combined statistics. If unavailable or version-incompatible, the page labels the latest visible-history replay scope. Playback does not silently rewrite the original test.
- Metric export separates historical_test from latest_visible_replay when the original MIA artifact is available.

## Authority and verification
Implementation: templates/algorithms.html, templates/base.html, and static/app.css. Reusable system: DESIGN.md and .impeccable/design.json. Evaluation source: core/views.py and artifacts/mia-continuous-evaluation.json. Existing result capture: .impeccable/review/monitor-results-mobile.jpg. The fresh risk reviewer returned SHIP; no new result-layout capture is claimed by this documentation pass.

## Content guardrails
Keep combined synthetic-test results distinct from the live playback stream. Explain denominators and synthetic-data limits. Do not display algorithm names, raw model scores, theory, parameters, or diagnostics anywhere in the analyst interface. Algorithm theory remains in docs/ALGORITHMS.md; forecasts remain profile-only.

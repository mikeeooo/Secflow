# Algorithms surface

Status: shipped refinement of the incumbent minimalist blue and white workspace. User-facing title: Rezultate; route: /algorithms/. No approved image comp. Context loader and detector remain unavailable because the bundled engine is missing. This record uses current source and the completed visual review.

## Purpose
Compare readable results produced automatically by the background detection engine, one evaluation source at a time. Algorithm run, parameter, and import controls do not appear in the analyst frontend.

## Composition
1. Heading and subtitle describe automatically calculated results. Exportă rezultate appears when an analysis exists.
2. Rezultate pe datele de test shows the run time, evaluation count, and duration, followed by a Sursa datelor selector and Afișează.
3. The table compares Isolation Forest, LOF, DBSCAN, and Scor combinat for the selected source. Precizie, Acoperire, F1, and Alarme false have short explanations. The combined row has a pale blue background and stronger text.
4. Captions distinguish test, reference, and validation counts and state that sources are evaluated separately; metrics describe the local subset.
5. Rezultate detaliate și validare is closed by default, with confusion counts by split and a threshold/exclusion note.
6. Experiment separat: PaySim original appears only when benchmark data exists, closed by default, with its separate cohort, thresholds, table, limitations, and export.

## States and behavior
- No published run: Analiză în pregătire explains that the engine will publish results after processing.
- Choosing a source and submitting Afișează shows that source's statistics; evaluation populations remain separate.
- At 760px the source filter wraps and tables scroll with the Romanian swipe hint.
- There are no algorithm execution, parameter, or dataset-import forms, including for administrator users on this page.

## Authority and verification
Implementation: templates/base.html, templates/algorithms.html, static/app.css, and static/app.js. Reusable system: DESIGN.md and .impeccable/design.json. Visual review reports no material UI findings. Current evidence: .impeccable/review/mia-desktop-results.jpg (1440px) and .impeccable/review/mia-mobile-results.jpg (390px). This pass verified source consistency without changing the UI.

## Content guardrails
Keep statistics intuitive and source-separated. Preserve the distinction between local simulation metrics and bank performance. Algorithm theory stays in docs/ALGORITHMS.md; technical configuration belongs to backend/administration. No forecast values appear in result or customer lists.

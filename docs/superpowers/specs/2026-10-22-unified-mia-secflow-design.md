# Unified MIA SecFlow design

## Intended outcome

Deliver one canonical local university demo inside the Secflow repository. Use the synthetic MIA dataset, FastAPI contracts, historical feature engine, model training, risk policy, audit and evaluation from `mia_university_demo`. Present those capabilities through a React interface with the light SecFlow visual language and clear analyst workflows. Keep the existing Django app as legacy reference while the unified app is validated.

## Boundaries

- The synthetic MIA population remains separate from PaySim. Do not merge identities or imply MIA transaction provenance.
- Python owns data generation, feature extraction, models, SQLite, decisions and evaluation. React calls FastAPI through the typed API client.
- Preserve chronological splits, private evaluation labels, idempotent assessment and review handling, and distinct payment/decision/review states.
- The 0–100 score is an anomaly ranking, not a fraud probability. DBSCAN findings are separate investigation evidence.
- Implement the complete six-stage plan already realized in the source project, including the first three weeks, then verify its transfer into this repository.

## Integration

The canonical application lives at `mia_university_demo/` in this repository. Copy source, configuration, lockfiles, synthetic dataset, model artifacts and evaluation evidence. Exclude virtual environments, installed packages, caches and build output. The root README points to the canonical app; the legacy Django checkout remains available for visual and historical reference.

## Interface

Use SecFlow's light neutral canvas, pale structural sidebar, white surfaces, restrained blue actions, generous table spacing and Romanian analyst copy. Keep the six MIA routes and API behavior. Show synthetic provenance and score meaning in the shell and investigation. At narrow widths the navigation is dismissible, focus remains visible, and touch targets remain usable. Press feedback is immediate; reduced motion and reduced transparency have static, legible alternatives.

## Acceptance

The Python test suite, TypeScript check and production frontend build pass from the new location. The local API serves health and overview; the frontend loads backend data and simulator-to-investigation remains functional. Desktop and mobile views are inspected. Documentation states the canonical run path and measured limitations.

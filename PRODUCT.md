# SecFlow
<!-- impeccable:product-schema 1 -->
## Platform
web
## Stack
Django, SQLite, server-rendered HTML, CSS and JavaScript, confirmed from BLUEPRINT.md.
## Users and purpose
University prototype for a banking fraud analyst monitoring simulated MIA instant payments. Fictional named customers have accounts, transaction histories and past cases. The three algorithms run automatically in a persistent background queue. Analysts investigate results and correct restrictions. Forecast alert volume appears only after opening a selected customer profile; lists show current risk signals.
## Capabilities and constraints
Five primary pages, auditable decisions, explainable risk, and from-scratch Isolation Forest, DBSCAN and LOF. PaySim and generated scenarios are separate evaluation populations. No banking integration. Scores are not calibrated probabilities.
## Brand commitments
Romanian interface. Minimalist blue and white. Show essential tasks and results first; secondary operational details may expand. Algorithm theory belongs only in docs/ALGORITHMS.md, never on the platform. The analyst frontend shows results, not algorithm theory or run/parameter controls. Statistics remain intuitive; technical configuration belongs to the backend/administration. No Django administration link in the platform navigation. Direct code build approved by the user.
## Evidence
The latest user clarifications, README.md and data/generated/manifest.json describe the current simplified scope and dataset. BLUEPRINT.md preserves the initial specification. Older non-ML plans are superseded.

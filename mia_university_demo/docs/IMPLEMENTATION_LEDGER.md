# Implementation decisions

- The canonical application lives in `mia_university_demo/` inside the Secflow repository. Its Python/data pipeline came from the MIA demo and its current visual direction came from the parent SecFlow frontend. The parent Django application is preserved as a legacy reference.
- The updated plan superseded Streamlit with React/TypeScript/Vite/Tailwind/shadcn-style components. Streamlit code and dependency were removed.
- Python owns generation, historical features, model fitting, scoring, SQLite and audit state. React consumes typed JSON through `/api` only.
- The supplied development run uses 10,000 requests and 400 accounts. The generator accepts larger volumes, including 150,000 requests, but the delivered measurements come only from the 10,000-request run.
- The fixed 100-day synthetic window ends on 20 October 2026 so demo requests on the build date have recent history. Frozen dates and seed make the experiment reproducible.
- Assessment scores are anomaly ranks, not probabilities. Historical rows without live assessment are labeled as such; DBSCAN findings show availability time.
- The source project's browser verification checked six areas, mobile width, simulator-to-investigation, refresh without resubmission, and failure/retry with the same transaction ID. The integrated SecFlow visual pass is recorded in `docs/INTEGRATION.md`.

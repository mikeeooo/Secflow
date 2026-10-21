# Unified MIA SecFlow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the MIA backend and synthetic dataset the canonical SecFlow demo, presented with the SecFlow interface style.

**Architecture:** A FastAPI/SQLite service and offline Python pipeline remain independent of React. React consumes typed JSON through `/api`; the previous Django app remains a legacy reference in the repository.

**Tech Stack:** Python 3.12, FastAPI, scikit-learn, SQLite, React, TypeScript, Vite, CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-10-22-unified-mia-secflow-design.md`

## Global Constraints

- The MIA dataset is synthetic and distinct from PaySim.
- ML labels are evaluation-only; scoring uses observable history available at decision time.
- Risk score is a rank, not a probability; payment, decision and review are distinct.
- Preserve the source project's lockfiles and its deterministic generator and evaluation CLI.

## Review Focus

- Repeated assessment and approval requests create at most one mock transfer.
- Equal-time or delayed events never leak future observations into features.
- New-location paths load models, policy, dataset and reports correctly.
- Mobile navigation and dialog operation remain keyboard accessible.
- API failure never appears as a successful payment and retains retry identity.

---

### Task 1: Relocate the complete MIA application

**Files:** Create `mia_university_demo/` with `src/`, `frontend/src/`, `config/`, `tests/`, dataset, artifacts and docs. Modify root `README.md`.

**Interfaces:** Preserve `mia-demo` CLI, `mia_demo.api:app`, `/api` JSON contract and frontend scripts.

- [x] Record the source manifest and baseline checks.
- [x] Copy project inputs and generated demonstration evidence, excluding installed and cache files.
- [x] Recheck copied manifest and paths; update README to the canonical run commands.

### Task 2: Apply SecFlow's visual system and Apple interaction guidance

**Files:** Modify `mia_university_demo/frontend/src/App.tsx`, `mia_university_demo/frontend/src/styles.css`, and relevant pages/components.

**Interfaces:** Keep existing routes and API calls unchanged; update shell, overview and common controls.

- [x] Compare source and target desktop/mobile views and record visual criteria.
- [x] Implement the light shell, structural sidebar, typography, tables, buttons and responsive behavior.
- [x] Verify keyboard focus, mobile dismissal, press feedback and reduced-motion/contrast/transparency alternatives.

### Task 3: Verify the integrated demo end to end

**Files:** Modify only files needed to fix concrete integration defects; record evidence in `mia_university_demo/docs/`.

**Interfaces:** `pytest`, `tsc`, `npm run build`, `/api/health`, `/api/overview`, simulator and persisted investigation.

- [x] Run the Python suite and frontend build in the new location.
- [x] Start the API and frontend locally, exercise data reads and a simulated payment.
- [x] Inspect the available browser viewport and document observed limits and exact run commands.

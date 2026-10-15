# Overview surface

Status: shipped refinement of the incumbent minimalist blue and white workspace. User-facing title: Monitorizare. No approved image comp. Context loader and detector remain unavailable because the bundled engine is missing. This record uses current source and the completed visual review.

## Purpose
Prioritize current risk signals and active cases in a fictional MIA payment portfolio. Open a named customer for history and the on-demand alert estimate.

## Composition
1. Primary navigation reads Monitorizare, Tranzacții, Cazuri, Clienți și conturi, Rezultate. The top bar identifies MIA instant payments; the footer identifies the simulation and fictional clients.
2. Heading and supporting sentence sit beside Vezi tranzacțiile.
3. A muted status row shows Analiză automată în fundal, the simulation clock, and a queued-request count when present.
4. Three metrics show Tranzacții MIA, Cazuri active, and Conturi blocate; the latter two link to their lists.
5. Necesită atenție lists fictional customer names and public account identifiers alongside amount/currency, current risk, Romanian decision badges, and case links. Customer names open their profiles.
6. Ultimele transferuri shows simulation dates, named senders and recipients, amounts, and current decisions.

## States and behavior
- No active cases: Niciun caz activ în portofoliu.
- Background scoring uses a persistent queue; this analyst surface offers no algorithm run, parameter, or import controls.
- Read-only monitoring pages check for changed results every seven seconds, skip hidden pages or focused fields, and reload when the revision changes. Temporary connection failures retain existing results.
- At 760px all three metrics remain in one row with smaller spacing and type. Tables scroll with the Romanian swipe hint; actions wrap and navigation becomes horizontal.
- Lists show current risk signals, never forecast values. Estimates appear only after opening a selected customer profile.

## Authority and verification
Implementation: templates/base.html, templates/dashboard.html, static/app.css, and static/app.js. Reusable system: DESIGN.md and .impeccable/design.json. Visual review reports no material UI findings. Current evidence: .impeccable/review/mia-desktop-dashboard.jpg (1440px) and .impeccable/review/mia-mobile-dashboard.jpg (390px). This pass verified source consistency without changing the UI.

## Content guardrails
Keep names, public account identifiers, MDL demo amounts, and calendar dates within the clearly simulated portfolio context. Preserve source/currency distinctions. Show current risk rather than forecast data in every list. Risk scores are not fraud probabilities. Algorithm theory belongs only in docs/ALGORITHMS.md.

# Overview surface

Status: shipped Apple-inspired Romanian white and blue redesign. Monitorizare; route: /. User-selected direction and direct code build. The final visual reviewer cleared desktop 1440px, user-width 799px, and phone 390/375px; all 48 application tests passed in the implementation handoff. This documentation pass changes no implementation.

## Purpose
Monitor synthetic MIA transfers through concise telemetry, then open alerts, cases, or a selected customer for investigation. The automatic demonstration scenario is enabled; detection stays in the background.

## Composition
1. A 216px neutral navigation rail with outline SVG icons, white MIA top bar, and neutral canvas establish location and identity. The current primary destination is solid blue; at 1023px the rail becomes a labeled Meniu control with expandable destinations. Primary destinations remain Monitorizare, Tranzacții, Cazuri, Clienți și conturi, Rezultate.
2. Direct 1 oră, 6 ore, and 24 ore links select the simulation interval with a visible current state. A separate playback action is blue when starting/replaying and secondary while running. The desktop heading has Vezi tranzacțiile.
3. A connection line states automatic updates every three seconds. Measured status reports worker health, simulation time, playback state, and remaining transfers.
4. A single white bordered aggregate strip contains four metrics: Transferuri, Semnale de risc actuale (with the current alert rate), Cazuri active (whole portfolio), and Volum solicitat (MDL demo in the selected interval).
5. Activitatea transferurilor charts 12 observed time buckets with solid blue transfers and dashed ochre current-risk signals. Current alert counts use the stored explanatory score and its review threshold. Numeric scale/time labels, a matching solid/dashed legend, final-bucket count labels, point titles, an accessible description, and Valorile graficului accompany the SVG.
6. Deciziile transferurilor shows original permitted/review/blocked decisions at receipt, with counts, percentages, and meters; pending and reference requests are separate.
7. An unboxed health strip shows queued work, average recent latency in milliseconds, and failed requests.
8. Alerte recente lists named fictional customers, simulation times, amounts, current score, explicitly labeled original decision, and case links. Scores link to the transaction causes through Vezi cauzele. Ultimele transferuri lists the latest selected-interval transfers. Profile links lead to history and the on-demand estimate.

## States and behavior
- Each data-live region updates independently every three seconds. Controls stay outside replacement regions; playback buttons update to the returned state.
- Focus inside a panel, an open disclosure, or a horizontally scrolled table freezes that panel. An explicit notice gives the displayed data's age while unrelated panels continue refreshing. Once interaction ends, its next update resumes replacement.
- Connection failures retain current panels and show Reconectare automată. Worker health derives from the recent heartbeat, rather than a decorative always-active state.
- Empty active cases and empty selected-interval transfers have distinct messages. Missing latency shows a dash. Paused and completed scenarios are explicitly labeled.
- At 850px summary metrics form a 2×2 grid and telemetry panels stack; decisions form a three-column row. At 620px the heading shortcut is hidden, the toolbar wraps, and monitoring values use clamp(20px, 6.4vw, 28px) without breaking numbers. The playback action retains its 44px minimum height.
- At 620px enhanced alert and transfer tables become labeled two-column records with identity spanning the full row; unenhanced tables retain horizontal scrolling and the Romanian hint. On list pages, a quiet Actualizează lista button offers new rows explicitly.
- Current score and original decision remain separate; stored initial decisions and cases are preserved.
- Lists show observed risk only. Per-customer forecasts are computed only after opening a selected profile.

## Authority and verification

Current implementation: templates/dashboard.html, templates/dashboard_panels.html, templates/base.html, static/app.js, core/monitoring.py, and static/app.css. Reusable tokens and components: DESIGN.md and .impeccable/design.json. The handoff reports completed visual review and 48 passing tests; this pass checked documentation consistency, JSON, and whitespace without rerunning browser review.

## Content guardrails
Use the selected simulation interval consistently; active cases explicitly cover the whole portfolio. Show measured queue, heartbeat, latency, and failures. Keep names, account identifiers, MDL demo, and dates clearly simulated. Algorithm names, raw model scores, parameters, and diagnostics are absent from the analyst frontend. Risk scores are not fraud probabilities; estimates never appear in lists.

# Overview surface

Status: shipped refinement of the incumbent Romanian white and blue workspace. User-facing title: Monitorizare. No approved image comp or quality card. Context loader and detector remain unavailable because the bundled engine is missing. This pass records corrected source and refreshed desktop/mobile captures. The final reviewer returned ship for the scoped corrections.

## Purpose
Monitor synthetic MIA transfers through concise telemetry, then open alerts, cases, or a selected customer for investigation. The automatic demonstration scenario is enabled; detection stays in the background.

## Composition
1. A pale navigation rail with outline SVG icons, white MIA top bar, and pale wash workspace establish location and identity. Primary destinations remain Monitorizare, Tranzacții, Cazuri, Clienți și conturi, Rezultate.
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
- At 760px summary metrics form a 2×2 grid; telemetry panels stack. The compact toolbar and shell bring the chart into the first viewport. The heading shortcut is hidden; grouped direct range links and a minimum-44px playback action wrap as needed. Tables retain the Romanian swipe hint.
- Recent-alert identity cells retain a 185px minimum width and do not wrap; the table scrolls horizontally so customer names and public identifiers remain readable on mobile.
- Current score and original decision remain separate. The risk extension received SHIP with no material findings; the related transaction/profile captures are recorded in their surface briefs.
- Lists show observed risk only. Per-customer forecasts are computed only after opening a selected profile.

## Authority and verification
Implementation: templates/dashboard.html, templates/dashboard_panels.html, templates/base.html, static/app.css, static/app.js, and core/monitoring.py. Reusable system: DESIGN.md and .impeccable/design.json. The code-led refinement applies UI/UX Pro Max together with Impeccable within the inherited visual world. Refreshed current captures: .impeccable/review/monitor-desktop.jpg and monitor-mobile.jpg. The documentation pass checked source consistency; the final reviewer cleared the scoped visual findings.

## Content guardrails
Use the selected simulation interval consistently; active cases explicitly cover the whole portfolio. Show measured queue, heartbeat, latency, and failures. Keep names, account identifiers, MDL demo, and dates clearly simulated. Algorithm names, raw model scores, parameters, and diagnostics are absent from the analyst frontend. Risk scores are not fraud probabilities; estimates never appear in lists.

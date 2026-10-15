# Customer profile surface

Status: shipped within the incumbent minimalist blue and white workspace. User-facing heading is the fictional customer's name; route: /accounts/<id>/. No approved image comp. Context loader and detector remain unavailable because the bundled engine is missing. This record uses current source and the completed visual review.

## Purpose
Investigate one customer's current risk, transaction history, prior cases, and restrictions. Calculate an indicative next-hour alert-volume estimate only when this profile is opened.

## Composition
1. The fictional customer name leads the page; its public account identifier, current restriction state, and Client fictiv appear below. Înapoi la clienți returns to the list.
2. Three summary columns show sent/received requests, maximum initial risk, and closed case count.
3. Estimarea alertelor · următoarea oră pairs an approximate count with a chart: six historical hourly bars in pale blue and one next-hour forecast bar in action blue. Counts, relative hour labels, and an accessible description reinforce the color distinction.
4. Istoricul tranzacțiilor shows simulated calendar times, named parties, amount/currency, and decisions, with a link to all transactions.
5. Dosarele clientului shows case links, simulated opening times, status, outcome, and closure date. Prepared historical cases carry Istoric demonstrativ.
6. Gestionează restricția contului is closed by default. It contains a required reason and the appropriate block/unblock action, followed by restriction events. Prior refused transactions remain blocked.
7. Detalii sursă și dispozitive is closed by default and contains the original source account ID and simulated device identifiers.

## States and behavior
- With recent observations, show the estimate, last-six-hour request/alert counts, and the orientative-estimate explanation. This is alert volume, not fraud probability.
- Without recent observations, show the concise no-recent-requests message and omit the chart/count.
- Empty history and case tables state their absence clearly.
- At 760px the forecast panel stacks with a 25px gap; the chart retains all seven bars. Tables scroll and all three summary columns remain visible.
- The forecast is computed on profile access. Monitoring, transaction, and customer lists show current risk signals and do not show or calculate per-customer forecasts.

## Authority and verification
Implementation: templates/account.html, core/views.py, static/app.css, and static/app.js. Reusable system: DESIGN.md and .impeccable/design.json. Visual review reports no material UI findings. Current evidence: .impeccable/review/mia-desktop-profile.jpg (1440px), .impeccable/review/mia-mobile-profile.jpg (390px), and supplemental .impeccable/review/mia-desktop-history.jpg. This pass verified source consistency without changing the UI.

## Content guardrails
Names, public account identifiers, MDL demo amounts, and calendar dates belong to the simulation. Preserve original source identifiers in secondary detail. Keep the next-hour quantity labeled as an indicative alert-volume estimate; never present it as a fraud probability or put it in lists. Algorithm theory remains in docs/ALGORITHMS.md.

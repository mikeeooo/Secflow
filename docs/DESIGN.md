# Interface design notes

SecFlow is a quiet analyst tool with a single dark appearance (Grafana-style surfaces), chosen for
long monitoring sessions. Navigation uses a sidebar and system type; identity lives in one place.

## The signature: the risk composition bar

Every assessment draws its 0–100 index as the literal sum of its four weighted parts
(0.35·IF + 0.25·LOF + 0.10·DBSCAN + 0.30·rules), with the validated Verify and Block thresholds
marked on the same scale. Under the bar, each part prints its own arithmetic (`0.35 × 0.94 = 32.9`).

This is the product's point of view: a decision is only as good as its explanation. Everything
around the bar stays neutral.

## Tokens (dark only)

| Role | Value | Contrast on panel `#16171C` |
|---|---|---|
| Canvas / panel / raised | `#0B0C0F` / `#16171C` / `#202228` | — |
| Label / secondary | `#F2F2F5` / `#A5A7B0` | 16.0:1 / 7.5:1 |
| Accent (links, focus) | `#4DA3FF` | 6.8:1 |
| Filled buttons | `#0A6FD6` (primary), `#C4372B` (destructive) | white text 4.9:1 / 5.4:1 |
| Permitted | `#32D74B` | 9.3:1 |
| Needs verification | `#FFB340` | 10.0:1 |
| Preventive risk block | `#FF6961` | 6.3:1 |
| Confirmed fraud evidence | solid `#F2F2F5` badge, dark text | 16:1 |

The light dark-mode accent and red cannot carry white text (about 2.7:1), so filled buttons use the
deeper `*-strong` fills.

Decision states always pair an icon with the text label (check, hourglass, ban, shield), so colour
is never the only signal.

Confirmed evidence uses a solid inverse badge rather than another hue. It reads as authoritative,
stays distinct from the red preventive block, and leaves the chart hues free.

Chart categorical slots for the four components are blue `#3987E5`, magenta `#D55181`, violet
`#9085E9`, and aqua `#199E70`, checked with the dataviz palette validator against the `#16171C`
panel. An earlier all-blue ramp failed the lightness, chroma, and normal-vision checks, and an
aqua–magenta adjacency failed deuteranopia separation. The order above passes all hard gates.

Every chart still carries direct text values or a data table, and segments keep 2px surface gaps.

The DBSCAN cluster graph rotates slowly (one turn in about 80 seconds) around its centroid. It
holds still while the pointer is over it, has a pause control, and starts paused when the system
asks for reduced motion.

## Type and layout

- **Type.** The system stack (SF Pro on Apple platforms) at a 15px body size; 12px is the smallest
  text. Large titles are 28–32px bold display. All figures use tabular numerals.
- **Navigation.** A 248px sidebar on wide screens. Below 1024px it becomes a header with a
  navigation sheet (44px targets, Escape closes, focus moves to the close button).
- **Responsive lists.** Rows use a two-line layout (names and amount, then time, risk, and decision)
  so they read at any width. Component legends and key–value grids use container queries, so they
  respond to their card rather than the viewport.
- **Progressive disclosure.** On phones, advanced transaction filters sit behind "More filters"; they
  are open by default on wider screens.
- **Accessibility.** Reduced motion disables the arrival highlight and transitions. A skip link,
  visible focus rings, labelled controls, and `role=status`/`alert` regions support keyboard and
  screen-reader use.

## Copy

Interface text uses consistent terms: **Confirmed fraud evidence**, **Preventive risk block**,
**Needs verification**, **Permitted**. Scores are called an "anomaly-risk index", never a
probability. Success states say "recorded as permitted" and "simulated outcome only: no funds
moved", never that a transfer was sent.

# Interface design notes

SecFlow is a quiet analyst tool. The design follows Apple's Human Interface Guidelines as
principles for a web app (sidebar navigation, semantic colours, system type, light and dark
appearance with no in-app toggle). Identity lives in one place.

## The signature: the risk composition bar

Every assessment draws its 0–100 index as the literal sum of its four weighted parts
(0.35·IF + 0.25·LOF + 0.10·DBSCAN + 0.30·rules), with the validated Verify and Block thresholds
marked on the same scale. Under the bar, each part prints its own arithmetic (`0.35 × 0.94 = 32.9`).

This is the product's point of view: a decision is only as good as its explanation. Everything
around the bar stays neutral.

## Tokens

| Role | Light | Dark | Text contrast |
|---|---|---|---|
| Canvas / surface | `#F2F2F7` / `#FFFFFF` | `#000000` / `#1C1C1E` | — |
| Label / secondary | `#1D1D1F` / `#6E6E73` | `#F5F5F7` / `#A1A1A6` | 16.8:1 / 5.1:1 on white |
| Accent (links, primary) | `#0066CC` | `#4DA3FF` | 5.7:1 on white |
| Permitted | `#1E7D34` | `#32D74B` | 5.2:1 on white |
| Needs verification | `#9A5B00` | `#FFB340` | 5.4:1 on white |
| Preventive risk block | `#C42B1C` | `#FF6961` | 5.6:1 on white |
| Confirmed fraud evidence | solid `#1D1D1F` badge, white text | solid `#F5F5F7` badge, dark text | 16:1 |

Decision states always pair an icon with the text label (check, hourglass, ban, shield), so colour
is never the only signal.

Confirmed evidence uses a solid inverse badge rather than another hue. It reads as authoritative,
stays distinct from the red preventive block, and leaves the chart hues free.

Chart categorical slots for the four components are blue `#2A78D6`, magenta `#E87BA4`, violet
`#6250D6`, and aqua `#1BAF7A` (dark: `#3987E5`, `#D55181`, `#9085E9`, `#199E70`). They were checked
with the dataviz palette validator in both modes. The first candidate, an all-blue ramp, failed the
lightness, chroma, and normal-vision checks, and an aqua–magenta adjacency failed deuteranopia
separation in dark mode. The order above passes all hard gates.

Magenta and aqua are below 3:1 against white, so every chart carries direct text values or a data
table. Segments keep 2px surface gaps.

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

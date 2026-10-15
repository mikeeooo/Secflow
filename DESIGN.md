---
name: SecFlow
description: A minimalist Romanian blue and white workspace for simulated payment investigations.
colors:
  primary: "#2259da"
  primary-hover: "#1745ad"
  nav: "#f7f9fd"
  ink: "#172641"
  muted: "#627087"
  line: "#e2e8f1"
  wash: "#f5f8fe"
  surface: "#ffffff"
  danger: "#a53738"
  success: "#226749"
  warning: "#895e12"
  focus: "#83a6ff"
  nav-active: "#e6edff"
  nav-active-text: "#194ebf"
  nav-hover: "#edf2fc"
  field-border: "#ccd5e3"
  block-bg: "#fceced"
  review-bg: "#fff4db"
  allow-bg: "#ebf5ee"
  historical-bar: "#c9d8fa"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "44px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-.03em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "28px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-.025em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "17px"
    fontWeight: 650
    lineHeight: 1.4
    letterSpacing: "-.015em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-.03em"
  monitor-metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-.03em"
  forecast:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "normal"
  risk-score:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "40px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-.025em"
  table-body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  table-label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.55
    letterSpacing: "normal"
rounded:
  badge: "5px"
  control: "7px"
  panel: "12px"
  range: "9px"
spacing:
  compact: "8px"
  control: "12px"
  inset: "16px"
  mobile: "20px"
  section: "24px"
  workspace: "44px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-active:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  button-secondary-hover:
    backgroundColor: "{colors.wash}"
  button-secondary-active:
    backgroundColor: "{colors.nav-active}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  navigation-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.nav-active-text}"
    rounded: "{rounded.control}"
    padding: "11px 14px"
  badge-block:
    backgroundColor: "{colors.block-bg}"
    textColor: "{colors.danger}"
    rounded: "{rounded.badge}"
    padding: "4px 9px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
  disclosure-summary:
    textColor: "{colors.ink}"
    padding: "18px 0"
  forecast-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "25px"
  forecast-number:
    textColor: "{colors.ink}"
    typography: "{typography.forecast}"
  monitor-metric:
    textColor: "{colors.ink}"
    typography: "{typography.monitor-metric}"
  risk-score:
    textColor: "{colors.ink}"
    typography: "{typography.risk-score}"
  risk-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "25px"
  time-range:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.range}"
    padding: "4px"
  time-range-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.nav-active-text}"
    rounded: "{rounded.badge}"
    padding: "5px 15px"
---

# Design System: SecFlow

## Overview

**Creative North Star: "The Analyst’s Desk"**

The Analyst’s Desk is a restrained working environment: white content surfaces on a pale blue wash, a pale navigation rail, clear blue actions, and readable operational data. The user-approved direction is minimalist blue and white; the metaphor describes the implemented result rather than a separately approved visual concept.

Flat boundaries and measured spacing let telemetry, numbers, and investigation actions carry the hierarchy. The monitoring language takes its cue from Grafana and Prometheus while retaining the incumbent white and blue workspace. Romanian labels keep the university prototype direct and understandable. Essential measurements remain visible; secondary operational detail opens through native disclosures. This records the current code. No approved image comp or quality card exists.

**Key Characteristics:**
- White content surfaces on a pale blue wash with a pale blue-gray navigation rail.
- Blue actions and selection states, with restrained semantic status colors.
- System typography, tabular numbers, and compact readable tables.
- Flat bordered containers, native disclosures, and visible keyboard focus.

## Colors

A clear action blue anchors cool neutrals; muted red, amber, and green communicate operational status. Frontmatter values are the source of truth for the documented palette.

### Primary
- **Action Blue** (`primary`): links, primary actions, the brand mark, disclosure markers, and input caret.
- **Deep Action Blue** (`primary-hover`): primary button hover.
- **Selection Blue** (`nav-active`, `nav-active-text`): the current navigation destination.
- **Focus Blue** (`focus`): the keyboard focus outline.
- **Historical Blue** (`historical-bar`): observed bars in the customer alert-volume chart; the future estimate uses Action Blue.

### Neutral
- **Paper White** (`surface`): the top bar, controls, panels, and aggregate strip.
- **Navigation Mist** (`nav`): the navigation rail, disabled fields, and login background.
- **Ink Navy** (`ink`): primary text and headings.
- **Slate Text** (`muted`): secondary labels, captions, and descriptions.
- **Cool Divider** (`line`): panel boundaries and structural separators.
- **Blue Wash** (`wash`): the workspace canvas, secondary hover states, and informational surfaces.
- **Field Border** (`field-border`): the control boundary.
- **Navigation Hover** (`nav-hover`): destination hover background.

### Semantic status
- **Muted Red** (`danger`, `block-bg`): Blocată decisions and invalid field borders.
- **Forest Green** (`success`, `allow-bg`): Permisă decisions.
- **Ochre** (`warning`, `review-bg`): De verificat decisions, the dashed alert series, unavailable processing status, and paused-panel notices.

**The Explicit State Rule.** Every decision badge includes a text label; color reinforces meaning.

## Typography

**Display Font:** system sans-serif, using the `display` stack.
**Body Font:** the same system sans-serif stack. No external font is loaded.

The typography is compact and neutral. Metric and amount values use tabular numerals where defined; identifiers wrap in detail views.

### Hierarchy
- **Display:** login introduction; the largest headline role, reduced to 32px on mobile.
- **Headline:** page headings, with compact tracking and a reduction to 26px on mobile.
- **Title:** section headings and panel titles.
- **Body:** general content; paragraphs cap their measure at 72 characters.
- **Metric:** general summary counts with tabular numerals, reduced to 27px on mobile; results use 30px on mobile.
- **Monitor Metric:** the denser four-value telemetry summary; 25px at the compact desktop breakpoint and 24px on mobile.
- **Forecast:** the approximate alert-volume estimate, with a quieter regular weight and a smaller unit label.
- **Risk Score:** current explanatory risk, reduced to 36px on mobile; the denominator uses quieter 15px type.
- **Table Body:** readable transaction and investigation rows.
- **Table Label:** sentence-case column headings, with normal tracking and medium weight.

The exact base roles are normative in frontmatter. Supporting labels range from 10 to 13 pixels in the existing code; they do not introduce separate font families. Form labels use 12px and fields use 13px. Shared badges use 12px. Risk summaries use 13px; highlighted fact labels/descriptions use 12px, with descriptions at 1.6 line height and tabular point values. Secondary explanations sit below metric labels or values.

## Layout

The desktop shell has a fixed navigation rail (224px), a top bar (76px), and a content container capped at 1400px with horizontal padding of 44px. The rail becomes 200px at widths up to 1100px, while content padding falls to 26px. At widths up to 760px it becomes an in-flow horizontal navigation strip, with 20px content padding and a 48px top bar. The audit and staff-only test-request links remain available on mobile; Django administration is not linked from the platform; the rail simulation note is hidden there, while the footer retains the simulation context.

Panels have a 24px bottom margin. Two-column detail layouts use a 24px gap and stack at 760px. Transaction risk uses a wider first column (1.6fr) and narrower facts column (.8fr, minimum 250px); at 1100px this becomes 1.3fr:1fr with a 220px facts minimum. The risk panel comes first in DOM order and remains first when stacked. Risk evidence uses two columns with a 26px gap, becoming one column at 1100px inside transaction details and at 760px elsewhere. Monitoring uses a single white bordered aggregate strip with four summary columns, becoming a 2×2 grid on mobile. The strip has 20px vertical padding on desktop and 16px on mobile. Customer profiles retain three summary columns; the three result metrics stack on mobile. Tables scroll horizontally and use a 580px minimum width on mobile, with a visible swipe instruction. Monitoring table rows use 12px vertical cell padding. Page headings and action groups wrap.

The telemetry grid places a wider time-series panel beside decisions (1.9:1, 20px gap), narrows to 1.65:1 at 1100px, and stacks with an 18px gap at 760px. The time-series SVG is 180px high, reduced to 160px on mobile. The mobile monitoring page uses 20px top padding, an 18px heading margin, a compact direct-range/playback toolbar, and no heading-level transaction shortcut. On mobile the toolbar wraps as needed; three range links remain grouped. Playback retains a 44px minimum height.

The forecast panel uses a 1.2:1 split with a 40px gap. At 760px it stacks with a 25px gap. Its seven-column chart is 140px high with 14px gaps and room beneath for hour labels. Restriction forms cap their width at 580px. Processing health and evaluation counts use wrapping inline rows.

Print hides navigation, filters, buttons, and footer; panels avoid internal page breaks and tables lose the mobile minimum width. Surface composition belongs in `.impeccable/surfaces/`, rather than the reusable system.

## Elevation & Depth

The implemented system has no shadows. White panels are separated by fine borders, spacing, and pale background shifts. A three-pixel focus outline with a three-pixel offset creates interaction emphasis without changing layout.

**The Flat Surface Rule.** Use the established borders and tonal separation for panels; the current system does not define raised surfaces.

## Shapes

Panels have gently curved corners using the panel radius. Controls and navigation items use the smaller control radius; badges use the badge radius. Avatar and status dots are circular. Containers normally use a one-pixel border. Nested disclosure tables have an eight-pixel radius. Chart bars have small rounded upper corners and a flat baseline.

## Components

### Buttons
Primary buttons are compact, blue, and semibold, with the control radius and a minimum height of 42px. Secondary actions have white backgrounds, ink text, and a divider-colored border. Hover changes the background over 0.18 seconds. Active primary actions use the deep blue; active secondary actions use the selection background. Focus uses the shared outline. Disabled buttons reduce opacity to 0.65 and show a wait cursor. The transparent Ieșire action is muted, becoming blue on a pale hover surface. Forms marked for busy feedback replace their action text and disable that action while submitting. Reduced-motion preferences remove transitions.

### Chips
Decision badges are small rounded rectangles with explicit Romanian labels. Blocată, De verificat, and Permisă each have a pale semantic background and darker text. Neutral badges use a cool gray treatment. These badges communicate state and are not interactive controls.

### Cards / Containers
White panels have a thin divider-colored border, the panel radius, no shadow, and clipped overflow. Section headings own their padding (23px 24px 18px); padded panels use 25px, reduced to 20px on mobile. Tables sit inside a separate horizontal scrolling wrapper. Table headings use normal sentence case. Monitoring charts and decisions share one telemetry grid; compact processing measurements sit beneath it. Results use three labeled percentage metrics with explanations and a short inline count row.

### Inputs / Fields
White inputs have ink text, a cool field border, the control radius, and a minimum height of 42px. Labels appear above fields with a 7px gap. Fields use the shared keyboard focus outline. Textareas resize vertically. Disabled fields use the navigation background, muted text, and a not-allowed cursor. Invalid fields use a danger-colored border. Form feedback also uses separate success/error message surfaces.

### Navigation
The sidebar uses a pale background, stacked destinations with a 6px gap, and a current-page blue treatment. Each primary destination pairs text with an 18px outline SVG icon (1.7px stroke); icons become 16px on mobile. Text and icon share a row with an 11px gap, reduced to 7px on mobile. Hover uses a lighter blue surface. Current destinations are marked with `aria-current="page"`. On mobile destinations become a horizontally scrolling row; auxiliary navigation remains below. The current primary destination scrolls into view. A skip link becomes visible when focused.

### Workspace Metrics
Summary values sit in a shared row with separators and tabular counts. The monitoring row is one white bordered container using the panel radius. The monitoring variant has four columns and reflows to two on mobile; the customer profile has three columns throughout. Results have three columns on desktop and one on mobile. Scope captions beneath monitoring values distinguish the selected interval from the whole portfolio. The surface records define the counts.

### Disclosures
Native details/summary controls place secondary information behind a clear Romanian label. The summary uses a blue native marker, a pointer cursor, a text hover change to blue, and the shared keyboard focus outline. A fine bottom border anchors the row. The summary has 18px vertical padding; expanded content has 7px above and 24px below. Keep the default closed state used by the current surfaces.

### Monitoring Status
A compact, muted row pairs the status dot with measured processing health, the simulation clock, and playback state. Active processing uses blue; unavailable processing uses ochre and explicit text. The reusable status row has a fine top border; the monitoring-page variant removes that border and top padding to align with the toolbar and aggregate strip. A separate connection line states the three-second refresh interval or a connection/retry error. Queue size, average recent processing latency, and failed requests appear in an unboxed wrapping strip.

### Time Range and Playback
Three direct range links (1 oră, 6 ore, 24 ore) share a compact white bordered group with the range radius. The selected range uses the navigation selection colors and `aria-current`. The adjacent playback action is blue when starting or replaying, and secondary while the scenario is running. Its wording and style update together with the returned playback state. Keep these controls outside live panel replacement.

### Live Panels
Each dashboard panel refreshes independently. A panel with focused content, an open disclosure, or a horizontally scrolled table pauses replacement and shows an ochre notice with the age of its displayed data. Other panels continue updating. Closing the disclosure, leaving focus, or resetting horizontal scroll permits the next update to replace that panel. Do not imply that frozen content is current.

### Time Series and Decisions
The transfer series uses a solid action-blue line and point markers. Alerts use a thinner dashed ochre line. A light grid, numeric scale labels, simulation time labels, a matching solid/dashed legend, final-bucket count labels, accessible SVG description, point titles, and an expandable values table make the chart readable beyond color. Decision summaries pair explicit counts and percentages with slim meters. These are observed simulation values; the profile estimate remains a separate component.

### Explainable Risk
Current risk pairs a large tabular score, explicit Scăzut/Moderat/Ridicat status, and a nine-pixel meter. The shared semantic colors reinforce status; text and the numeric value retain meaning independently. A short ink-colored summary leads into Indicatori de risc and Elemente favorabile. Each fact uses a compact heading, concrete description, thin top divider, and tabular point contribution when relevant. Favorable facts provide context; they are not negative-point deductions. The full contribution list and rounding sit in a native disclosure. Current scores remain distinct from original decisions and historical risk. Score links use Vezi cauzele beneath the value.

### Customer Alert Estimate
The existing flat padded panel pairs an approximate alert count with a seven-bar chart. Six historical bars use Historical Blue; the next-hour bar uses Action Blue. Bars have a 65% column width, a minimum height of 3px, and rounded top corners. Visible counts and relative hour labels accompany the accessible chart description. The quantity uses the forecast type role and an explicit alerte unit. The customer-profile record owns its placement and empty state.

## Do's and Don'ts

### Do:
- Do use the documented blue and white palette for the analyst workspace.
- Do accompany decision colors with explicit Permisă, De verificat, or Blocată text.
- Do retain visible keyboard focus and the skip-to-content link.
- Do preserve horizontal table scrolling and its Romanian mobile hint when columns exceed the viewport.
- Do keep essential tasks visible and secondary operational details in clearly labeled disclosures.
- Do keep the shared simulation and risk-score context readable.
- Do pair current risk with concrete causes, favorable facts, and an explicit score/status; keep the original decision clearly labeled.

### Don't:
- Don't encode operational decisions through color alone.
- Don't replace Romanian task labels with untranslated interface copy.
- Don't describe risk scores as fraud probabilities.
- Don't combine amounts from different currency units into one unqualified total.
- Don't expose algorithm names, raw model scores, or technical configuration in the analyst interface.
- Don’t link Django administration from the platform navigation.

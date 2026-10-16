---
name: "SecFlow"
description: "An Apple-inspired Romanian analyst workspace in white and blue."
colors:
  blue: "#0066cc"
  blue-hover: "#0054a8"
  ink: "#1d1d1f"
  muted: "#626873"
  wash: "#f5f5f7"
  nav: "#f0f1f4"
  surface: "#ffffff"
  line: "#e1e3e8"
  field: "#a9afba"
  selection: "#e8f1fc"
  danger: "#b42332"
  danger-bg: "#fff0f1"
  success: "#25704c"
  success-bg: "#edf7f1"
  warning: "#8a5600"
  warning-bg: "#fff5e3"
  range-track: "#e9ebef"
  historical-bar: "#7b9ac5"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "42px"
    fontWeight: 650
    lineHeight: 1.14
    letterSpacing: "-.035em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "32px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-.035em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-.02em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.6
    letterSpacing: "normal"
  table-label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.6
    letterSpacing: "normal"
  metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "34px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-.035em"
  monitor-metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-.035em"
  phone-monitor-metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "clamp(20px, 6.4vw, 28px)"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-.035em"
  risk-score:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-.035em"
  forecast:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "40px"
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "-.03em"
  result-metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "42px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-.035em"
rounded:
  badge: "6px"
  segment: "7px"
  navigation: "9px"
  control: "10px"
  panel: "16px"
spacing:
  compact: "8px"
  control: "12px"
  inset: "16px"
  mobile: "20px"
  section: "24px"
  panel: "28px"
  workspace: "40px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  button-primary-hover:
    backgroundColor: "{colors.blue-hover}"
  button-primary-active:
    backgroundColor: "{colors.blue-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  button-secondary-hover:
    backgroundColor: "{colors.nav}"
  button-secondary-active:
    backgroundColor: "{colors.selection}"
  button-list-update:
    backgroundColor: "transparent"
    textColor: "{colors.blue}"
    rounded: "{rounded.control}"
    padding: "9px 10px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  navigation-active:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.surface}"
    rounded: "{rounded.navigation}"
    padding: "10px 12px"
  badge-block:
    backgroundColor: "{colors.danger-bg}"
    textColor: "{colors.danger}"
    rounded: "{rounded.badge}"
    padding: "4px 9px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
  disclosure-summary:
    textColor: "{colors.ink}"
    padding: "18px 0"
  time-range:
    backgroundColor: "{colors.range-track}"
    rounded: "{rounded.control}"
    padding: "4px"
  time-range-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.segment}"
    padding: "6px 18px"
  monitor-metric:
    textColor: "{colors.ink}"
    typography: "{typography.monitor-metric}"
---

# Design System: SecFlow

## Overview

**Creative North Star: "The Apple-inspired Analyst’s Desk"**

The user-selected Apple-like white and blue direction defines a quiet Romanian workspace: neutral canvas, white grouped panels, a compact navigation rail, generous headings, and clear blue actions. System typography and restrained separators keep attention on the analyst’s next task.

Essential values stay visible; secondary evidence opens through native disclosures. Stable controls, explicit list updates, and focus-preserving live panels protect reading and investigation. This record describes the shipped stylesheet; surface composition lives in .impeccable/surfaces/.

**Key Characteristics:**
- Neutral canvas and white panels with restrained borders.
- System typography, tabular numbers, and generous page headings.
- Blue primary actions and a solid blue current navigation destination.
- Collapsible tablet navigation and labeled phone records.
- Quiet updates, native disclosures, and visible keyboard focus.

## Colors

### Primary
Action Blue (`blue`) marks links, primary actions, focus, and the current primary destination; Deep Action Blue (`blue-hover`) marks pressed and hovered actions. Selection Tint (`selection`) supports notices and auxiliary selection. Historical Blue (`historical-bar`) distinguishes observed profile bars from the blue estimate.

### Neutral
Soft Canvas (`wash`) surrounds Paper White (`surface`) panels. Navigation Gray (`nav`) supports the rail and disabled controls. Graphite (`ink`) carries headings and values; Slate (`muted`) carries secondary context. Fine Divider (`line`) separates groups; Field Edge (`field`) defines controls. Segment Track (`range-track`) holds the time selector.

### Semantic status
Red (`danger`, `danger-bg`), green (`success`, `success-bg`), and amber (`warning`, `warning-bg`) reinforce blocked, permitted, review, and error states with explicit Romanian labels.

**The Explicit State Rule.** Every decision and risk state has a text label; color reinforces meaning.

## Typography

**Display Font:** system sans-serif from the `display` token.
**Body Font:** the same system stack; no downloaded font.

Headlines are generous and tightly tracked. Body copy stays readable and caps paragraphs at 72ch. Amounts, scores, and counts use tabular numerals. Frontmatter owns base sizes; responsive variants are listed below.

- Display: login heading, reduced to 34px at 850px and 30px at 620px.
- Headline/title: page and panel headings, reduced to 28px/17px on phones.
- Metric: general summary values; profiles use 26px phone values in labeled rows.
- Monitor metric: 28px at 1250px, 30px at 1023px, then the `phone-monitor-metric` clamp at 620px. Values use `white-space: nowrap` and `overflow-wrap: normal`; unit captions can wrap.
- Risk score: 44px on phones, with a quieter 16px denominator. Forecast count retains an explicit alert unit.
- Result metric: 36px on phones. Table headers use sentence case; phone record labels use 11px.
- Fields: 14px on desktop and 16px on phones; label and error text remain adjacent.

**The Whole Number Rule.** Monitoring values remain indivisible on phones; responsive type fits the number before its unit wraps.

## Layout

The desktop shell uses a fixed 216px sidebar, a minimum-64px top bar, and a content container capped at 1440px with 40px horizontal padding. Padding becomes 32px at 1250px, 24px at 1023px, and 20px at 620px. White panels use a 24px bottom gap and 28px internal padding; phone panels use a 20px gap and 24px by 20px padding.

At 1023px and below, navigation becomes an in-flow header with a labeled Meniu toggle. Its expanded destinations form three columns, then two at 620px. JavaScript progressively collapses the menu; without it, links remain accessible. The workspace loses its sidebar offset and the top bar becomes minimum 56px.

Monitoring uses four metrics and a wide activity chart beside decisions. At 850px metrics become 2×2, telemetry stacks, and three decisions share one row. At 620px tables enhanced with column labels become two-column records with the identity spanning the full row. Unenhanced tables retain a 560px minimum width, horizontal scrolling, and a Romanian swipe hint.

Detail panels use a 24px gap. Transaction risk leads visually and in DOM order; its detail grid stacks at 850px. Evidence groups stack at 1250px inside the narrow two-panel layout, return to two columns when that layout stacks, and become one column at 620px. Forecast content and generic detail layouts stack at 620px. Result metrics and evaluation counts become single-column there.

Print hides navigation, filters, actions, and the footer; panels avoid page breaks and table minimum widths are removed. Composition and data scope belong in the surface records.

## Elevation & Depth

Fine borders and neutral background shifts separate flat panels. The selected time segment has the only shadow (`0 1px 3px #1d1d1f14`). Keyboard focus uses a three-pixel Action Blue outline with a three-pixel offset. Button and navigation state changes use 180ms transitions with `cubic-bezier(.2,.8,.2,1)`; reduced-motion preferences disable transitions and animations.

**The Quiet Depth Rule.** Panels stay flat; only the selected time segment uses a small shadow.

## Shapes

Panels use the panel radius; fields and actions use the control radius. Navigation destinations, selected time segments, and badges use their smaller frontmatter radii. Avatar and status dots are circular. Borders are normally one pixel; meters and chart bars use small rounded ends.

## Components

### Buttons
Blue primary and white bordered secondary actions have a 44px minimum height and medium weight (550). Primary hover/active uses Deep Action Blue; secondary hover uses Navigation Gray and active uses Selection Tint. Disabled actions use 0.55 opacity and a wait cursor. The quiet Actualizează lista action is a blue text button inside a white bordered notice; it does not compete with the page action. Busy forms disable their submit action and update its wording.

### Chips
Compact noninteractive badges pair semantic backgrounds with darker text. Their Romanian labels carry the decision or case state independently of color.

### Cards / Containers
White bordered panels use the panel radius and clipped overflow. Section headings have 24px/24px/20px padding, reduced to 22px/20px/18px on phones. Tables and data panels share the same typography and separators.

### Inputs / Fields
White fields use Field Edge borders, the control radius, 44px minimum height, and the shared focus outline. Invalid fields use red borders and adjacent errors; a linked error summary receives focus. Server validation preserves entered values for correction. Disabled fields use Navigation Gray; textareas resize vertically.

### Navigation
Primary links pair outline icons with Romanian labels. The current destination is solid blue with white text and `aria-current`; hover uses the divider tone. Auxiliary current links use blue on Selection Tint. On compact layouts, Meniu exposes the destination grid and Escape closes it with focus returned to the toggle. A visible-on-focus skip link reaches main content.

### Metrics and tables
Shared summary rows align tabular values with quiet labels. Monitoring uses one bordered white group; phone values follow the Whole Number Rule. Phone records retain each table column’s label. Pagination wraps while previous/next controls remain reachable.

### Disclosures and live updates
Native details/summary controls keep secondary evidence closed by default. Their marker is muted; hover becomes blue and keyboard focus remains visible. Live dashboard panels update independently every three seconds. Focus, an open disclosure, or horizontal table inspection pauses only the affected panel and exposes the age of its displayed data. Stable toolbar controls stay outside replacement regions. Lists offer an explicit update action without replacing the record being read.

### Time selector and charts
The gray segmented time selector uses a white selected segment with quiet shadow, ink text, and `aria-current`. Playback is blue for start/replay and secondary while running. The activity chart pairs a solid blue transfer line with a dashed amber alert line, scale and time labels, accessible descriptions, and an expandable data table. Endpoint labels are hidden on phones; the data table retains exact values. Profile forecasts use six observed bars and one blue next-hour estimate.

### Explainable risk
Current risk combines a tabular score, text status, semantic meter, concrete drivers, favorable context, and a full-contribution disclosure. Favorable facts do not subtract points. Initial decisions and historical risk retain distinct labels; forecasts remain a separate alert-count quantity on the selected customer profile.

## Do's and Don'ts

### Do:
- Do use the Apple-inspired neutral canvas, white panels, system font, and blue action vocabulary.
- Do retain visible keyboard focus, explicit field labels, and the skip link.
- Do present phone tables as labeled records when enhanced; retain scrolling and its hint as a fallback.
- Do preserve focused or expanded live content, filter state, and invalid form drafts.
- Do distinguish current risk, original decisions, and profile-only alert counts.

### Don't:
- Don't split a monitoring number across lines on phones.
- Don't encode decisions through color alone.
- Don't replace Romanian task labels with untranslated copy.
- Don't describe the 0–100 risk score as a fraud probability or rewrite initial decision history.
- Don't expose algorithm names, raw model scores, configuration, or Django administration in the analyst navigation.

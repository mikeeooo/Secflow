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
  forecast:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1.3
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
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  button-secondary-hover:
    backgroundColor: "{colors.wash}"
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
---

# Design System: SecFlow

## Overview

**Creative North Star: "The Analyst’s Desk"**

The Analyst’s Desk is a restrained working environment: white content surfaces, a pale navigation rail, clear blue actions, and readable operational data. The user-approved direction is minimalist blue and white; the metaphor describes the implemented result rather than a separately approved visual concept.

Flat boundaries and measured spacing let tables, numbers, and investigation actions carry the hierarchy. Romanian labels keep the university prototype direct and understandable. Essential tasks and results remain visible; secondary operational detail opens through native disclosures. This records the shipped code. No approved image comp exists.

**Key Characteristics:**
- White content surfaces with a pale blue-gray navigation rail.
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
- **Paper White** (`surface`): the page, controls, and panels.
- **Navigation Mist** (`nav`): the navigation rail, disabled fields, and login background.
- **Ink Navy** (`ink`): primary text and headings.
- **Slate Text** (`muted`): secondary labels, captions, and descriptions.
- **Cool Divider** (`line`): panel boundaries and structural separators.
- **Blue Wash** (`wash`): secondary hover states and informational surfaces.
- **Field Border** (`field-border`): the control boundary.
- **Navigation Hover** (`nav-hover`): destination hover background.

### Semantic status
- **Muted Red** (`danger`, `block-bg`): Blocată decisions and invalid field borders.
- **Forest Green** (`success`, `allow-bg`): Permisă decisions.
- **Ochre** (`warning`, `review-bg`): De verificat decisions.

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
- **Metric:** large workspace counts with tabular numerals, reduced to 27px on mobile.
- **Forecast:** the approximate alert-volume estimate, with a quieter regular weight and a smaller unit label.
- **Table Label:** sentence-case column headings, with normal tracking and medium weight.

The exact base roles are normative in frontmatter. Supporting labels range from 10 to 13 pixels in the existing code; they do not introduce separate font families. Form labels use 12px and fields use 13px. Secondary column explanations sit below their labels.

## Layout

The desktop shell has a fixed navigation rail (224px), a top bar (76px), and a content container capped at 1400px with horizontal padding of 44px. The rail becomes 200px at widths up to 1100px, while content padding falls to 26px. At widths up to 760px it becomes an in-flow horizontal navigation strip, with 20px content padding and a 60px top bar. The audit and staff-only test-request links remain available on mobile; Django administration is not linked from the platform; the rail simulation note is hidden there, while the footer retains the simulation context.

Panels have a 24px bottom margin. Two-column detail layouts use a 24px gap and stack at 760px. Monitoring and customer-profile summaries retain three equal columns on mobile, with smaller labels, counts, and cell padding. Tables scroll horizontally and use a 580px minimum width on mobile, with a visible swipe instruction. Page headings and action groups wrap.

The forecast panel uses a 1.2:1 split with a 40px gap. At 760px it stacks with a 25px gap. Its seven-column chart is 140px high with 14px gaps and room beneath for hour labels. Restriction forms cap their width at 580px. The monitoring status row wraps with a 10px gap, and the results data-source filter wraps on mobile.

Print hides navigation, filters, buttons, and footer; panels avoid internal page breaks and tables lose the mobile minimum width. Surface composition belongs in `.impeccable/surfaces/`, rather than the reusable system.

## Elevation & Depth

The implemented system has no shadows. White panels are separated by fine borders, spacing, and pale background shifts. A three-pixel focus outline with a three-pixel offset creates interaction emphasis without changing layout.

**The Flat Surface Rule.** Use the established borders and tonal separation for panels; the current system does not define raised surfaces.

## Shapes

Panels have gently curved corners using the panel radius. Controls and navigation items use the smaller control radius; badges use the badge radius. Avatar and status dots are circular. Containers normally use a one-pixel border. Nested disclosure tables have an eight-pixel radius. Chart bars have small rounded upper corners and a flat baseline.

## Components

### Buttons
Primary buttons are compact, blue, and semibold, with the control radius and a minimum height of 42px. Secondary actions have white backgrounds, ink text, and a divider-colored border. Hover changes the background over 0.18 seconds. Focus uses the shared outline. Disabled buttons reduce opacity to 0.65 and show a wait cursor. The transparent Ieșire action is muted, becoming blue on a pale hover surface. Forms marked for busy feedback replace their action text and disable that action while submitting. Reduced-motion preferences remove transitions.

### Chips
Decision badges are small rounded rectangles with explicit Romanian labels. Blocată, De verificat, and Permisă each have a pale semantic background and darker text. Neutral badges use a cool gray treatment. These badges communicate state and are not interactive controls.

### Cards / Containers
White panels have a thin divider-colored border, the panel radius, no shadow, and clipped overflow. Section headings own their padding (23px 24px 18px); padded panels use 25px, reduced to 20px on mobile. Tables sit inside a separate horizontal scrolling wrapper. Table headings use normal sentence case; result-column explanations appear below them. The combined-result row uses the blue wash and stronger text weight.

### Inputs / Fields
White inputs have ink text, a cool field border, the control radius, and a minimum height of 42px. Labels appear above fields with a 7px gap. Fields use the shared keyboard focus outline. Textareas resize vertically. Disabled fields use the navigation background, muted text, and a not-allowed cursor. Invalid fields use a danger-colored border. Form feedback also uses separate success/error message surfaces.

### Navigation
The sidebar uses a pale background, stacked destinations with a 6px gap, and a current-page blue treatment. Hover uses a lighter blue surface. Current destinations are marked with `aria-current="page"`. On mobile destinations become a horizontally scrolling row; auxiliary navigation remains below. The current primary destination scrolls into view. A skip link becomes visible when focused.

### Workspace Metrics
Three summary values sit in one shared row with separators. Labels appear above large tabular counts. The mobile layout preserves all three columns while reducing spacing and type size. The surface records define the specific counts.

### Disclosures
Native details/summary controls place secondary information behind a clear Romanian label. The summary uses a blue native marker, a pointer cursor, a text hover change to blue, and the shared keyboard focus outline. A fine bottom border anchors the row. The summary has 18px vertical padding; expanded content has 7px above and 24px below. Keep the default closed state used by the current surfaces.

### Monitoring Status
A compact, muted row pairs the blue status dot with the background-analysis message, simulation clock, and queued-request count when present. It wraps naturally rather than using a separate raised container. Read-only monitoring lists refresh when new results arrive and preserve the current view during temporary connection failures.

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

### Don't:
- Don't encode operational decisions through color alone.
- Don't replace Romanian task labels with untranslated interface copy.
- Don't describe risk scores as fraud probabilities.
- Don't combine amounts from different currency units into one unqualified total.
- Don’t link Django administration from the platform navigation.

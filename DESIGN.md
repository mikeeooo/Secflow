---
name: SecFlow
description: A minimalist blue and white workspace for simulated payment investigations.
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
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "49px"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-.035em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "29px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-.03em"
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
    letterSpacing: "-.035em"
  table-label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "10px"
    fontWeight: 600
    lineHeight: 1.55
    letterSpacing: ".035em"
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
    padding: "11px 16px"
  badge-block:
    backgroundColor: "{colors.block-bg}"
    textColor: "{colors.danger}"
    rounded: "{rounded.badge}"
    padding: "4px 9px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
---

# Design System: SecFlow

## Overview

**Creative North Star: "The Analyst’s Desk"**

The Analyst’s Desk is a restrained working environment: white content surfaces, a pale navigation rail, clear blue actions, and readable operational data. The user-approved direction is minimalist blue and white; the metaphor here describes the implemented result rather than a separately approved visual concept.

The interface uses flat boundaries and measured spacing so tables, numbers, and investigation actions carry the hierarchy. English labels describe decisions and simulation limitations directly. This document records the current code; no approved image comp exists.

**Key Characteristics:**
- White content surfaces with a pale blue-gray navigation rail.
- Blue actions and selection states, with restrained semantic status colors.
- System typography, tabular numbers, and compact readable tables.
- Flat bordered containers and visible keyboard focus.

## Colors

A clear action blue anchors cool neutrals; muted red, amber, and green communicate operational status.

### Primary
- **Action Blue** (`primary`): links, primary actions, the brand mark, and input caret.
- **Deep Action Blue** (`primary-hover`): primary button hover.
- **Selection Blue** (`nav-active`, `nav-active-text`): the current navigation destination.
- **Focus Blue** (`focus`): the keyboard focus outline.

### Neutral
- **Paper White** (`surface`): the page, controls, and panels.
- **Navigation Mist** (`nav`): the navigation rail and login background.
- **Ink Navy** (`ink`): primary text and headings.
- **Slate Text** (`muted`): secondary labels, captions, and descriptions.
- **Cool Divider** (`line`): panel boundaries and structural separators.
- **Blue Wash** (`wash`): secondary hover states and informational surfaces.

### Semantic status
- **Muted Red** (`danger`, `block-bg`): Block decisions.
- **Forest Green** (`success`, `allow-bg`): Allow decisions.
- **Ochre** (`warning`, `review-bg`): Review decisions.

**The Explicit State Rule.** Every decision badge includes a text label; color reinforces meaning.

## Typography

**Display Font:** system sans-serif, using the `display` stack.
**Body Font:** the same system sans-serif stack. No external font is loaded.

The typography is compact and neutral. Metric and amount values use tabular numerals where defined; identifiers wrap in detail views.

### Hierarchy
- **Display:** login introduction; the largest headline role, reduced on mobile.
- **Headline:** page headings, with compact tracking and a mobile reduction.
- **Title:** section headings and panel titles.
- **Body:** general content; paragraphs cap their measure at 74 characters.
- **Metric:** large workspace counts with tabular numerals.
- **Table Label:** uppercase column headings with slight tracking.

The exact base roles are normative in frontmatter. Supporting labels range from 10 to 13 pixels in the existing code; they do not introduce separate font families.

## Layout

The desktop shell has a fixed navigation rail (224px), a top bar (87px), and a content container capped at 1540px with horizontal padding of 44px. The rail becomes 190px at widths up to 1100px, while content padding falls to 25px. At widths up to 760px it becomes an in-flow horizontal navigation strip, with 20px content padding. Audit and administration links remain available on mobile; the rail simulation note is hidden there, while the footer retains the simulation context.

Panels and two-column detail layouts use a 24px gap. Overview uses a 1.7:1 panel split, narrowed to 1.4:1 at 1100px and stacked at 760px. Four summary columns become two on mobile. Tables scroll horizontally and retain a 650px minimum width on mobile, with a visible swipe instruction. Headings and action groups wrap instead of compressing.

Print hides navigation, filters, buttons, and footer; panels avoid page breaks internally and tables lose the mobile minimum width. The overview composition is recorded separately in `.impeccable/surfaces/overview.md`.

## Elevation & Depth

The implemented system has no shadows. White panels are separated by fine borders, spacing, and pale background shifts. A three-pixel focus outline with a three-pixel offset creates interaction emphasis without changing layout.

**The Flat Surface Rule.** Use the established borders and tonal separation for panels; the current system does not define raised surfaces.

## Shapes

Panels have gently curved corners using the panel radius. Controls and navigation items use the smaller control radius; badges use the badge radius. Avatar and status dots are circular. Containers normally use a one-pixel border. Chart bars have small rounded upper corners and a flat baseline.

## Components

### Buttons
Primary buttons are compact, blue, and semibold, with the control radius. Secondary actions have white backgrounds, ink text, and a divider-colored border. The implemented hover transition changes the background over 0.18 seconds. Focus uses the shared outline. Disabled buttons reduce opacity to 0.6 and show a wait cursor. The text action used for Sign out is transparent and muted, becoming blue on a pale hover surface.

### Chips
Decision badges are small rounded rectangles with explicit labels. Block, Review, and Allow each have a pale semantic background and darker text. Neutral badges use a cool gray treatment. These badges communicate state and are not interactive controls.

### Cards / Containers
White panels have a thin divider-colored border, the panel radius, no shadow, and clipped overflow. Section headings own their padding; the padded panel variant uses 25px, reduced to 20px on mobile. Tables sit inside a separate horizontal scrolling wrapper.

### Inputs / Fields
White inputs have ink text, a cool field border, and the control radius. Labels appear above fields with a 7px gap. Fields use 13px text and the shared keyboard focus outline. Textareas resize vertically. The stylesheet does not define a custom disabled field style or per-field invalid state; form feedback uses separate success/error message surfaces.

### Navigation
The sidebar uses a pale background, stacked destinations, and a current-page blue treatment. Hover uses a lighter blue surface. Current destinations are marked with `aria-current="page"`. On mobile destinations become a horizontally scrolling row; auxiliary navigation remains below. A skip link becomes visible when focused.

### Workspace Metrics
Summary values sit in a single shared row with separators, rather than individual cards. Labels and explanatory captions surround large tabular counts. At the mobile breakpoint they reflow to two columns and remove the first divider of the second row.

## Do's and Don'ts

### Do:
- Do use the documented blue and white palette for the analyst workspace.
- Do accompany decision colors with explicit Allow, Review, or Block text.
- Do retain visible keyboard focus and the skip-to-content link.
- Do preserve horizontal table scrolling and its mobile hint when columns exceed the viewport.
- Do keep simulation provenance and uncalibrated-score explanations visible.

### Don’t:
- Don’t encode operational decisions through color alone.
- Don’t describe risk scores as fraud probabilities.
- Don’t combine amounts from different currency units into one unqualified total.

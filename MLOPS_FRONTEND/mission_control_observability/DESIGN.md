---
name: Mission Control Observability
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#181b25'
  surface-container: '#1c1f29'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2ef'
  on-surface-variant: '#bbc9cd'
  inverse-surface: '#dfe2ef'
  inverse-on-surface: '#2c303a'
  outline: '#859397'
  outline-variant: '#3c494c'
  surface-tint: '#2fd9f4'
  primary: '#8aebff'
  on-primary: '#00363e'
  primary-container: '#22d3ee'
  on-primary-container: '#005763'
  inverse-primary: '#006877'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffd6a7'
  on-tertiary: '#472a00'
  tertiary-container: '#ffb147'
  on-tertiary-container: '#704500'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#a2eeff'
  primary-fixed-dim: '#2fd9f4'
  on-primary-fixed: '#001f25'
  on-primary-fixed-variant: '#004e5a'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0f131c'
  on-background: '#dfe2ef'
  surface-variant: '#31353f'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: '700'
    lineHeight: 2.5rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
  label-code-lg:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: '500'
    lineHeight: 1.25rem
    letterSpacing: -0.01em
  label-code-md:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
  label-code-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '400'
    lineHeight: 0.875rem
  metric-display:
    fontFamily: JetBrains Mono
    fontSize: 1.75rem
    fontWeight: '700'
    lineHeight: 2rem
    letterSpacing: -0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system serves Site Reliability Engineers, incident commanders, and infrastructure architects operating in high-stakes production environments. The design aesthetic is rooted in **Mission Control Precision**: an austere, technical, dark-mode-first environment where critical telemetry can be parsed in milliseconds. 

The emotional tone balances calm authority with hyper-vigilance. Avoid generic B2B SaaS tropes—no purple/violet neon glows, no pastel decorative gradients, no playful micro-illustrations, and no emoji iconography. Visual affordances prioritize scannability, operational status immediacy, and dense, structured telemetry. Contrast is deliberate and surgical: background surfaces sink into an ultra-deep navy abyss, allowing functional signal colors (cyan, emerald, amber, red) to serve strictly as communicative vectors.

## Colors

The color architecture enforces a high-contrast functional hierarchy across dark spatial planes:

- **Base Canvas & Surfaces**:
  - `canvas`: `#0A0E17` (Deepest void navy-black)
  - `surface-panel`: `#111827` (Base panel and card fill)
  - `surface-elevated`: `#1A2234` (Hover layers, dropdowns, and flyouts)
  - `border-subtle`: `#1F2937` (Standard structural grid divider, 1px)
  - `border-strong`: `#374151` (Active controls and input boundaries)

- **Functional Telemetry Signals**:
  - **Primary / Active Action / Target**: `#22D3EE` (Cyan). Used for primary calls-to-action, focus indicators, interactive highlights, and active telemetry streams.
  - **Operational / Healthy**: `#10B981` (Emerald). Applied strictly to zero-error thresholds, nominal cluster statuses, and healthy uptime SLAs.
  - **Warning / Degraded**: `#F59E0B` (Amber). Allocated for latency anomalies, saturated memory limits, and non-blocking warnings under investigation.
  - **Critical / Sev-0 & Sev-1**: `#EF4444` (Pure Red). Reserved exclusively for operational outages, failed health checks, and destructive commands.

- **Status Badge Tinting Rule**: Status badges apply a strict `15%` alpha opacity background of the accent color matched with `100%` solid foreground text (e.g., Critical Badges use `rgba(239, 68, 68, 0.15)` background with `#EF4444` text).

## Typography

The typographic hierarchy implements a strict bifurcated system:

1. **Inter** manages UI navigation, section headers, standard descriptions, form field labels, and modal titles. Its neutral grotesque geometry provides effortless reading under sustained monitor exposure.
2. **JetBrains Mono** governs all data-bearing objects: log traces, query syntax, stack traces, IP/CIDR notations, container hashes, latency timers (ms/s), timestamps, and metrics.

### Technical Data Rules
- All numeric telemetry, data table cells, and status matrices must render in `JetBrains Mono` with tabular figures enabled (`tnum` font feature) to eliminate jitter during real-time streaming updates.
- Micro-labels such as environment tags (`prod-us-east-1`) and commit SHAs utilize `label-code-sm` set to uppercase or lowercase literals without stylistic modifications.

## Layout & Spacing

The layout is built upon an uncompromising **8px base grid** optimized for high-density dashboards, modular multi-pane split screens, and telemetry grids.

- **Grid Structure**: 12-column fluid grid for dashboard overview layouts; fixed-width modular side rails (56px collapsed icon rail, 240px contextual sub-navigation, and 360px collapsible incident triage flyout drawer).
- **Margins and Gutters**:
  - Desktop (>1440px): `1.5rem` outer canvas padding, `1rem` panel gutters.
  - Operations Wallboards (>1920px): Full-bleed viewport edges with fixed `1rem` gutters for perimeter-to-perimeter metric display.
  - Compact/Tablet (768px - 1024px): `1rem` outer canvas margins, stacking grid columns into single or double pane splits.
- **Density Guidelines**: Padding inside telemetry widgets and data tables stays condensed (`space-xs` to `space-sm`) to maximize visible log volume without vertical scrolling.

## Elevation & Depth

Visual hierarchy does not rely on diffused drop shadows or blurred glassmorphism, which introduce visual lag and muddy dark interfaces. Depth is achieved via **tonal layering and crisp, low-contrast structural outlines**:

- **Layer 0 (Canvas)**: `#0A0E17` baseline backdrop.
- **Layer 1 (Card & Module Surfaces)**: `#111827` enclosed by a 1px solid `#1F2937` border. No drop shadows.
- **Layer 2 (Overlays, Modals, & Context Menus)**: `#1A2234` bounded by a 1px solid `#374151` border with a subtle deep ambient shadow: `0 8px 24px -4px rgba(0, 0, 0, 0.6)`.
- **Focus & Selection**: Outlines overrule drop shadows. Interactive cards in an active state swap their border from `#1F2937` to `1px solid #22D3EE` with zero blur spread.

## Shapes

The design system uses a tight, industrial corner radius system that mirrors hardware rack-mount displays:

- **Panels, Modals, & Cards**: `8px` corner radius. Maintains structure without softening into consumer interfaces.
- **Form Controls & Buttons**: `6px` corner radius. Sharp, tactile, and engineered.
- **Badges, Pills, Status Indicators, & Tags**: `4px` corner radius. Retains a compact block profile suitable for inline code alignment.
- **Indicators & Node Dots**: Fully circular (`9999px`) for ping dots, status bulbs, and topology map vertices.

## Components

### Buttons
- **Primary**: Background `#22D3EE`, text `#0A0E17` (bold weight for high-contrast legibility), border `none`, border radius `6px`. On hover: `#06B6D4`.
- **Secondary (Outline)**: Background `transparent`, border `1px solid #374151`, text `#E5E7EB`. On hover: background `#1F2937`, border `#4B5563`.
- **Danger (Sev-1 Outage Actions)**: Background `transparent`, border `1px solid #EF4444`, text `#EF4444`. On hover: background `rgba(239, 68, 68, 0.15)`.
- **Ghost Action**: Background `transparent`, text `#9CA3AF`, no border. On hover: background `#1A2234`, text `#FFFFFF`.

### Cards & Panels
- Background `#111827`, border `1px solid #1F2937`, border radius `8px`, padding `1rem` or `1.5rem`.
- Panel headers feature an integrated 1px divider (`#1F2937`) separating section titles from child telemetry streams.

### Status Badges & Pills
- Border radius `4px`, padding `2px 8px`, typography `label-code-sm`.
- **Operational**: Background `rgba(16, 185, 129, 0.15)`, text `#10B981`, border `1px solid rgba(16, 185, 129, 0.2)`.
- **Warning**: Background `rgba(245, 158, 11, 0.15)`, text `#F59E0B`, border `1px solid rgba(245, 158, 11, 0.2)`.
- **Critical**: Background `rgba(239, 68, 68, 0.15)`, text `#EF4444`, border `1px solid rgba(239, 68, 68, 0.2)`.

### Form Inputs & Query Terminals
- Background `#0A0E17`, border `1px solid #374151`, border radius `6px`, text `#F9FAFB`, typography `Inter` (or `JetBrains Mono` for PromQL/LogQL query bars).
- Focus state: border `1px solid #22D3EE`, outline `none`.

### Incident & Telemetry Tables
- Header row: Background `#0E1420`, text `#9CA3AF`, uppercase `0.6875rem`, letter-spacing `0.05em`.
- Alternating zebra rows: Even rows `#111827`, odd rows `#0D131F`. Row borders: `1px solid #1F2937`.
- Metric numbers and timestamps right-aligned in `JetBrains Mono`. Hovered rows highlight to `#1A2234`.
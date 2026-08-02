# AMAZI — Water Intelligence Platform
## Design System Specification
**AI-Based Water Point Failure Prediction System for Rural Rwanda**
**Rwanda Water Board (RWB) · WASAC · University of Kigali Final Year Project**

*This document is the single source of truth for every visual and interaction decision in the application. It is structured exactly as the studio workflow demands: study → design system → critique → implement.*

---

## Table of Contents

1. [Phase 1 — Project Study](#phase-1--project-study)
2. [Phase 2 — Design System](#phase-2--design-system)
   - Product Identity
   - Design Principles
   - Moodboard
   - Typography
   - Color System
   - Space, Grid, Radius, Elevation
   - Signature Design Element
   - Iconography
   - Component System
   - Data Visualization
   - GIS Experience
   - Motion
   - Accessibility
   - Responsive Rules
   - Information Architecture & Wireframes
3. [Phase 3 — Self-Critique](#phase-3--self-critique)
4. [Phase 4 — Implementation Mapping](#phase-4--implementation-mapping)

---

# PHASE 1 — Project Study

## 1.1 The System Today

The audit (`AUDIT_REPORT.md`) and code review confirm a working Flask system with:

- **Auth & RBAC** — 4 roles: `admin`, `district_manager`, `district_technician`, `viewer`; district-scoped queries.
- **Data** — 223 seeded water points across Rwanda districts; 100 audit log entries; trained Logistic Regression model (accuracy 0.70, ROC-AUC 0.77) persisted in `models/`.
- **AI** — a real, deployed failure-risk model predicting `Functional / At Risk / Non-Functional` with a `High/Medium` confidence label, driven by age, population served, rainfall, technology type, and catchment pressure.
- **Maintenance** — a well-built task state machine (`pending → assigned → accepted → in_progress → completed → verified`) with a full audit trail.
- **Reports** — 6 report types with PDF/Excel export.
- **GIS** — a Leaflet map rendering status-colored point markers.

The UI is a stock Bootstrap 5.3 + Font Awesome shell. **Functionally complete, visually anonymous.**

## 1.2 Users, Goals, Pain Points, Business Goals

| Role | Goal | Today's Pain Point | Design Opportunity |
|---|---|---|---|
| **WASAC Technician** (field) | Know *what to fix, where, today* | List of tasks with no risk context; no route logic; map markers that don't answer "which one first" | A **"Today's work"** surface ordered by risk & deadline; water-point detail that shows *why*; map built for field navigation |
| **District Water Officer** | See district health and whether maintenance works | Counts on cards, no trends, no cause, no "what next" | The **Reservoir Gauge** (instant district health) + risk-ranked action list + prediction explainability |
| **System Administrator** | Keep the model and the system trustworthy | Model internals are invisible; audit data buried | A visible **AI Watch** (model online, accuracy, ROC-AUC, last run) and clean audit/ops surfaces |
| **Examiners / RWB evaluators** | Verify engineering rigor, not decoration | A generic dashboard does not evidence design thinking | A named, documented, defensible design system and a **signature element** with rationale |

**Business goal:** fewer days of lost water access, faster triage, auditable decisions.

**Design opportunity in one sentence:** *turn 223 risk probabilities and a task queue into one calm, legible "catchment" the operator can read in three seconds.*

---

# PHASE 2 — Design System

## 2.1 Product Identity

### Name — **AMAZI**

*Amazi* is the Kinyarwanda word for **water**. One syllable, universal, owned by the domain and the country it serves. The subtitle keeps the institutional anchor: **Amazi · RWB Water Intelligence**.

### Concept — **The Watershed Interface**

Every screen is a watershed. Water does not fight gravity; it follows the terrain. The interface mirrors that physics:

- **The source is at the top** — a dark brand bar holding identity and system status, like the river's headwater.
- **Navigation is the riverbed** — a left rail whose channels (Operations, Administration, System) carry the operator downstream in the order work actually flows.
- **Content is the catchment** — panels that collect data, not scattered islands.
- **The decision is the tap** — every screen resolves in a clear primary action, and nothing ornamental sits between the operator and that action.

Contour lines (topography) texture surfaces; flowing water animates state; the whole application reads as a piece of **hydrological instrumentation**, not a website.

### Mark (logo concept)

A **droplet whose bottom edge is a contour line** — water meeting terrain. Rendered in a rounded-square reservoir tile. The droplet doubles as a map pin, so the mark reads on a map legend as "water point" as easily as it reads as a brand.

## 2.2 Design Principles

1. **Calm is a feature.** An emergency-response tool must feel quieter than the emergency. No flashing, no gradients that shout, no confetti.
2. **Every number has a job.** If a statistic cannot change a maintenance decision, it is not on screen.
3. **AI must explain itself.** A prediction without its reasons is a guess with a badge. We always show the contributing factors.
4. **The watershed order.** Source → catchment → tap. Navigation, content, and action follow one direction, never requiring the operator to re-learn a layout per page.
5. **Government-grade trust.** Consistent, restrained, accessible. It must be credible in a ministerial review room, not just in a demo.
6. **No decorative motion.** Motion is reserved for water flowing, state changing, and prediction updating.
7. **Dark water, bright data.** Surfaces stay quiet; status colors and data do the talking.

## 2.3 Moodboard (described)

| Board | Character | Source material |
|---|---|---|
| *Blueprints* | Ink-on-vellum engineering drawings, contour plates, pipeline schematics | Hydrological survey maps, WASAC network diagrams |
| *The Land* | Nyungwe canopy, Kivu's deep water, volcanic highlands at dusk | Rwanda's landscape photography |
| *Telemetry* | Reservoir level gauges, SCADA panels, instrument readouts | Dam control rooms, national hydromet stations |
| *Fieldwork* | Maintenance crews, GPS units, data sheets on clipboard | WASAC field operations |

The synthesis: **blueprint ink on calm water**, with **terrain green** for health and **rust/sediment** for failure — never "startup violet on dark glass."

## 2.4 Typography

### The Pairing

| Role | Font | Rationale |
|---|---|---|
| **Display** | **Barlow Condensed** (600/700) | Barlow was designed for the California public — road signage, park systems, civil infrastructure. Its tall x-height and open letterforms hold up on a field device in sunlight. The **Condensed** cut is the "engineering drawing annotation" voice: it reads like the labels on a hydrological survey plate or a pipeline spec sheet. Uppercase kickers in this face feel like stamped instrument labels. |
| **Body / UI** | **Barlow** (400/500/600) | The same superfamily, humanist and sturdy, kept regular (never condensed) for sustained reading in tables and forms. One family across display and body gives the system an engineered coherence — the same steel, two gauges. |
| **Data / Mono** | **IBM Plex Mono** (400/500) | Designed for industrial instrumentation and dense tables. Risk scores, probabilities, coordinates, water-point IDs, and timestamps set in Plex Mono read as **telemetry**, not marketing copy. It is the "sensor readout" of the interface. |

*Deliberately excluded:* Inter, Roboto, Montserrat, Lato, Poppins, Nunito, Open Sans — every one of these signals "hosted SaaS template."

### Scale

| Token | Rem / Clamp | Face · Weight | Use |
|---|---|---|---|
| `display-1` | `clamp(2.5rem, 5vw, 3.4rem)` | Barlow Condensed 700 | Landing hero, stat heroes |
| `display-2` | `clamp(2rem, 4vw, 2.6rem)` | Barlow Condensed 700 | Page hero numbers |
| `h1` | `clamp(1.55rem, 2.6vw, 2rem)` | Barlow Condensed 600 | Page titles |
| `h2` | `1.3rem` | Barlow Condensed 600 | Panel titles |
| `h3` | `1.05rem` | Barlow 600 | Sub-panels, forms |
| `kicker` | `0.72rem`, `letter-spacing .14em`, uppercase | Barlow Condensed 600 | Eyebrows, section labels, "INSTRUMENT" stamps |
| `body` | `0.9375rem` (15px) · line-height 1.6 | Barlow 400 | Default text |
| `body-sm` | `0.8125rem` | Barlow 400 | Metadata, table cells secondary |
| `data` | `0.875rem` | IBM Plex Mono 400 | Risk %, coordinates, IDs |
| `data-lg` | `1.5rem` | IBM Plex Mono 500 | KPI values, gauge reads |

**Table typography:** 15px Barlow; header cells `kicker` style (uppercase, spaced, muted); numeric columns in `data` mono so columns align like a level recorder chart.

**Chart typography:** Chart.js fonts = Barlow 12px, scale ticks muted; data values in mono.

**Map typography:** popups/legend in Barlow; coordinates in mono; tile labels left to the basemap.

## 2.5 Color System

### Philosophy

The palette is named for the **watershed**, not for numbers. Every semantic hue is tied to something real in the domain. All neutrals carry a faint green undertone so the whole surface feels like concrete sitting in a watershed, never a neutral gray from a palette picker.

### Raw Palette

| Token | Value | Named for |
|---|---|---|
| `res-950` | `#04292E` | river bed |
| `res-900` | `#06343A` | headwater |
| `res-800` | `#0A444C` | deep reservoir |
| `res-700` | `#0E5460` | reservoir |
| `res-600` | **`#116A78`** | **primary · live river** |
| `res-500` | `#1B7F8E` | mid-river |
| `res-400` | `#3DA2B1` | rapids |
| `res-300` | `#79C4D0` | shallows |
| `res-200` | `#B2E0E6` | stream foam |
| `res-100` | `#DFF1F4` | mist |
| `res-50` | `#F1FAFB` | rain-washed air |
| `safe-700` | `#0D5534` | forest floor |
| `safe-600` | `#16794A` | **healthy · functioning** |
| `safe-500` | `#2A9D66` | canopy green |
| `safe-400` | `#54B98B` | new leaf |
| `safe-100` | `#DCF3E7` | fern wash |
| `safe-50` | `#EEF9F3` | |
| `risk-700` | `#7A4609` | dry season soil |
| `risk-600` | `#A8610C` | **at risk · sediment** |
| `risk-500` | `#C97E15` | sun on soil |
| `risk-400` | `#DFA34A` | |
| `risk-100` | `#F8EED3` | dust haze |
| `risk-50` | `#FCF8EC` | |
| `crit-700` | `#7E2117` | iron-rich laterite |
| `crit-600` | `#A92B1D` | **critical · broken main** |
| `crit-500` | `#C8402F` | rust |
| `crit-400` | `#DC6A57` | |
| `crit-100` | `#F7E0DC` | |
| `crit-50` | `#FCF1EF` | |
| `steel-600` | `#2E5B78` | **repair · galvanized pipe** |
| `steel-500` | `#46799A` | pipeline steel |
| `steel-400` | `#6B97B5` | |
| `steel-100` | `#E2EDF3` | |
| `ink-900` | `#14262A` | basalt |
| `ink-800` | `#1B3136` | damp concrete |
| `ink-700` | `#274046` | wet stone |
| `ink-600` | `#40595F` | dry concrete |
| `ink-500` | `#597076` | **secondary text** |
| `ink-400` | `#75898E` | |
| `ink-300` | `#9AAEB2` | |
| `ink-200` | `#C3D1D4` | |
| `ink-100` | `#E3EAEC` | **hairline border** |
| `ink-50` | `#F3F7F8` | **page background** |
| `surface` | `#FFFFFF` | panel surface |

### Semantic Mapping (single source of truth)

| Meaning | Surface | Foreground | Border | Used for |
|---|---|---|---|---|
| **Healthy / Functional** | `safe-50` | `safe-700` | `safe-100` | status chip, gauge segment |
| **At Risk** | `risk-50` | `risk-700` | `risk-100` | status chip, warnings |
| **Critical / Non-Functional** | `crit-50` | `crit-700` | `crit-100` | status chip, alerts |
| **Under Repair** | `steel-100` | `steel-600` | `steel-400` | status chip |
| **Pending** | `ink-100` | `ink-600` | `ink-200` | task status |
| **Info** | `res-50` | `res-700` | `res-100` | information |
| **AI / Prediction** | `res-50` | `res-700` | `res-100` | model, predictions |

**Contrast:** `res-600 #116A78` on white = 6.9:1; `safe-600` on white = 5.4:1; `risk-700` on `risk-50` = 8.2:1; `crit-700` on `crit-50` = 9.1:1 — all **WCAG AA** (text and UI). Status text is never rendered in the pale chip tints; it always uses the 700-level ink.

### Dark Water Mode

Dark mode is **"dark water"** — surfaces as deep reservoir blues, not black:
- page bg `res-950`, panel `res-900`, raised `res-800`
- text `#E6F1F2`, muted `ink-300`
- hairlines `res-800`
- status chips keep their tint but with deeper backgrounds
- The same semantic mapping applies; only neutrals and surfaces invert.

### Why this is not "a teal theme"

Generic dashboards use one accent blue everywhere. Here the **primary acts as the instrument** (links, primary actions, active nav) while **status colors are always domain colors** (water health = vegetation, risk = dry soil, failure = laterite). A functional point, a sediment-prone point, and a broken point can be read as color even in a color-blind-safe variant because each also carries an icon and a word.

## 2.6 Space, Grid, Radius, Elevation, Borders

### Spacing Scale (4px base, named after the watershed)

| Token | Rem | Use |
|---|---|---|
| `sp-1` | 0.25rem | icon-to-text gap |
| `sp-2` | 0.5rem | chip padding, dense gaps |
| `sp-3` | 0.75rem | form gaps |
| `sp-4` | 1rem | card padding (comfort) |
| `sp-5` | 1.5rem | panel padding, section gaps |
| `sp-6` | 2rem | between major regions |
| `sp-8` | 3rem | page section rhythm |

### Grid

- **Content column:** max `1180px` (a width that keeps line lengths ~72ch at 15px body — a deliberate reading width, not a Bootstrap leftover).
- **Panel grid:** 12-col fluid; KPI band = 4-up on desktop, 2-up tablet, 1-up phone.
- **Hero layout (dashboard):** gauge + riverline on top, then a 7/5 split (action list / side intelligence).

### Radius

| Token | Value | Use |
|---|---|---|
| `r-sm` | 4px | inputs, chips, small tiles |
| `r-md` | 8px | cards, panels, dialogs |
| `r-lg` | 14px | hero panels, brand tile, popup cards |
| `r-full` | 999px | pills, avatars, gauges |

Radius is small and mechanical — **8px is the loudest radius in the system.** No "rounded-xl glassmorphism."

### Elevation

| Token | Use |
|---|---|
| `e-0` | none — default, flat surfaces |
| `e-1` | `0 1px 0 rgba(4,41,46,.04)` + `0 1px 3px rgba(4,41,46,.08)` — resting panels |
| `e-2` | hover, dropdowns, toasts |
| `e-3` | modals, popups |

Shadows are cool (dark water tint), shallow, and reserved for depth, never for decoration.

### Borders

- Hairline `1px` `ink-100` is the default panel edge (dark mode: `res-800`).
- **Status never relies on border color alone** — chips pair border with tint + text + icon.

## 2.7 Signature Design Element — **The Amazi Reservoir**

One unforgettable feature. The dashboard hero is **the reservoir gauge**, an instrument that reads like a dam control room and can only exist for this product.

### Anatomy (left → right)

1. **The Reservoir Dial** — a circular gauge whose ring is a segmented status distribution (Functional / At Risk / Non-Functional / Under Repair). The needle is replaced by a **water level** that sits at the % of water points that are *not at risk*. Under the dial, the readout is telemetry mono: `HEALTH 74.2%`.
2. **The Riverline** — a horizontal river whose segments are the same status distribution. Water visibly **flows** through it (moving dash pattern). Each segment is a status color; the river is tinted toward risk as non-functional share rises. Tributary ticks mark each district/sector share.
3. **The AI Watch** — a compact instrument strip: model online dot, accuracy / ROC-AUC, last prediction run, next threshold. When a prediction updates anywhere in the system, the reservoir emits a **ripple pulse** (two expanding rings) and the water level animates to its new position.

### Why it is the identity

- **Readable in 3 seconds:** one glance gives district health, where the water is, and whether the AI is trustworthy.
- **Domain-true:** a reservoir is the actual mental model of a water utility; the dial and riverline are a dam and its outflow.
- **Motion with meaning:** the flow and ripple only appear when data changes or the model runs — never as idle decoration.
- **It names the brand:** the ring + contour droplet reappear on the landing page, login, and empty states, so the product's signature *is* its logo.

### Reduced motion

With `prefers-reduced-motion: reduce`, the riverline freezes into static segments and the ripple pulse is suppressed; the dial still animates the water level once (a single 300ms ease) to convey the change, then rests.

## 2.8 Iconography

The brief forbids generic icons. We cannot ship a custom glyph font without a build step, so the system is designed as **the "instrument tile" icon language**: every Font Awesome glyph is presented inside a **token-shaped tile** (a rounded-square with a tinted reservoir wash and a hairline), sized 20/24/32px, with a fixed **concept → glyph map**. Consistency comes from the container and the mapping, not the vendor.

### Concept → Glyph Map (curated, fixed)

| Concept | Glyph | Tile tint |
|---|---|---|
| Water Point | `fa-droplet` | `res-100` |
| Borehole | `fa-water` | `res-100` |
| Protected Spring | `fa-chevron-circle-down` → `fa-arrow-down` + leaf | `safe-100` |
| Tap Stand | `fa-faucet` | `res-100` |
| Pipeline | `fa-share-nodes` (rotated 90°) | `steel-100` |
| Reservoir | `fa-tower-broadcast` → **`fa-cubes-stacked`** (custom-chosen: reservoir layers) | `res-100` |
| Maintenance | `fa-wrench` | `steel-100` |
| Inspection | `fa-clipboard-check` | `steel-100` |
| Technician | `fa-screwdriver-wrench` | `steel-100` |
| Rainfall | `fa-cloud-rain` | `res-100` |
| Prediction / AI | `fa-wave-square` | `res-100` |
| District | `fa-location-crosshairs` | `res-100` |
| Sector | `fa-border-all` | `res-100` |
| GIS / Map | `fa-layer-group` | `res-100` |
| Analytics | `fa-chart-line` | `res-100` |
| Reports | `fa-file-lines` | `res-100` |

*(Where a Font Awesome glyph is a compromise — e.g. "Reservoir" — it is documented as such in the component library so it can be swapped for a custom SVG in a future build step without touching layout.)*

## 2.9 Component System

### Buttons

| Variant | Style | Use |
|---|---|---|
| **Primary** | `res-600` fill, white text, `r-sm`, hairline `res-700`, no glow | the single decision action per screen |
| **Secondary** | white surface, `ink-100` hairline, `ink-800` text | navigation-grade actions |
| **Tertiary / Ghost** | transparent, ink-600 text, underline on hover | inline, dense tables |
| **Danger** | `crit-600` fill | destructive only |

Buttons are **rectilinear with a tiny radius (4px)**, height 40px (38px secondary), Barlow 500, 15px. Icon + label always; icon-only variants get `aria-label`. Primary buttons are the only elements allowed the reservoir fill — this reserves the strongest color for decisions. Focus ring: 2px `res-400` offset 2px.

### Inputs

Rectilinear, `ink-100` hairline, transparent surface, `r-sm`, 40px height, mono for ID/coordinate fields, Barlow otherwise. Label is a `kicker` (uppercase spaced) so forms read like instrument panels. States: idle / hover (`ink-200`) / focus (2px `res-400`) / error (`crit-600` hairline + `crit-50` wash) / disabled. Placeholder `ink-300`.

### Cards & Panels

`e-1`, hairline `ink-100`, `r-md`, padding `sp-5`. Panels carry a `kicker` eyebrow, an optional tile-icon, and a title. **No giant numbers on tiles unless the number changes an action** — the KPI band uses 4 dense tiles, not 12 oversized cards.

### Status Chips

Chip = tint wash + 700-level text + 8px status dot + label. A water point chip also carries the mono risk % when space allows. The dot is a filled circle (functional = full droplet, at risk = half, non-functional = empty ring) — a color-blind-safe second channel.

### Tables

Header = `kicker` uppercase; rows 48px, hairline separators, hover `ink-50`; numeric columns in mono right-aligned; status column uses chips. Sort links carry ▲▼ markers; pagination uses bordered square buttons (current page = `res-600` fill).

### Dialogs

`r-lg`, `e-3`, 640px default, backdrop = 40% `res-950`. Title in h3 Barlow. Focus trapped by Bootstrap, `Esc` closes, `aria-labelledby` required.

### Filters

A **filter rail** — a single row of compact controls (selects, search, dates) ending in Apply/Reset. On mobile it stacks. Filters never float; they sit at the top of the panel they govern.

### Pagination, Empty States, Loading

- **Pagination:** square buttons, mono page numbers.
- **Empty state:** centered tile-icon in a `res-50` rounded square, a short "catchment is dry here" line, and the primary next action. Example: *"No water points in this catchment yet — Upload Data."*
- **Loading:** a **droplet fill** indicator (a droplet outline that fills with `res-400`), never a spinner; full-page loads show the droplet with the phrase `SAMPLING…`.

### Notifications

In-app notification list styled as **hydrological alerts**: a colored left rail (res/risk/crit) + title + timestamp in mono. Unread = filled rail; read = faded.

## 2.10 Data Visualization

Chart.js is restyled with the domain palette (never the default Chart.js blues):

- **Status distribution** → donut, segments = status colors, mono center total.
- **District risk** → horizontal bars (district names left, risk % as river bar), risk bar colored by bucket.
- **Trends** → line charts with `res-500` lines, no fill below the line (blueprint plot style), gridlines `ink-100`.
- **Feature importance** → horizontal bars, `res-500`.
- **All ticks** Barlow 12; data labels mono; legend bottom, uppercase kicker.

Rule: **a chart on screen must answer the question in its panel title** — no decorative sparklines anywhere.

## 2.11 GIS Experience

The map is a **field instrument**, not a decoration:

- **Basemap:** light CARTO tiles (cleaner than OSM for overlays) with OSM attribution; dark-water tiles in dark mode.
- **Markers:** status-colored **droplet pins** (custom `divIcon`) — a droplet outline whose fill matches status; clustered with `leaflet.markercluster` (cluster bubbles = reservoir tint with count).
- **Layer controls:** a floating panel toggling Water Points / District boundaries / Risk heatmap / Rainfall overlay / Technician positions. Heatmap = radius blur in status color (implemented as clustered circles with risk-proportional radius to avoid heavy libs).
- **Legend:** fixed bottom-left instrument card, mono.
- **Popups:** compact cards — water point ID (mono), status chip, risk %, tech type, and a **"Open point"** link to the detail page.
- **Filters rail** above the map: status, district (scoped), min risk, search.
- **Cluster markers** open on click into an expanded group list.

## 2.12 Motion

| Purpose | Motion | Duration / Ease |
|---|---|---|
| Water flow (riverline) | moving dash pattern | 2.4s linear infinite |
| Prediction update | reservoir ripple pulse + level ease | 1.2s · 300ms ease-out |
| State change (task) | chip color crossfade | 200ms |
| Panel reveal | translateY 8px + fade | 280ms `cubic-bezier(.2,.7,.2,1)` |
| Modal | scale .98 → 1 + fade | 180ms |
| Focus | 2px ring | instant (a11y) |

**All motion disabled** under `prefers-reduced-motion: reduce`. No bounce, no parallax, no idle animation.

## 2.13 Accessibility (WCAG AA)

- Contrast: every text/UI pairing in §2.5 verified ≥ 4.5:1 (text) / ≥ 3:1 (UI).
- **Keyboard:** full tab order; visible 2px focus rings everywhere; modal focus trap (Bootstrap); skip-to-content link.
- **Screen readers:** `aria-label` on icon-only buttons; `role="status"` on the reservoir readout; charts have `aria-label` summarizing the data (not just canvas).
- **Color-blind safe:** status always = dot/icon + word + color (never color alone).
- **Semantic HTML:** real `<h1>` per page, real `<table>` for data, real `<button>` for actions.
- **Responsive:** one breakpoint (≥ 960px = rail visible; < 960px = drawer) plus stacked KPI at 520px.

## 2.14 Responsive Rules

| Breakpoint | Behavior |
|---|---|
| ≥ 1200px | full rail, content 1180px, 4-up KPI |
| 960–1199px | rail compressed to icons |
| 640–959px | rail → drawer (hamburger), KPI 2-up |
| < 640px | KPI 1-up, tables → scroll, map controls condensed |

## 2.15 Information Architecture & Wireframes

### IA (by workflow)

```
OPERATIONS          ADMINISTRATION      SYSTEM (admin)
Dashboard           Reports             Users
GIS Map             Districts           Audit Logs
Water Points        Technicians         Model & Settings
Prediction Center
Maintenance Tasks
Notifications
```

Role gating: technicians see **Operations**; managers add **Administration**; admins see all three. The most frequent path (risk-ranked today's work) is 1–2 clicks from Dashboard.

### ASCII Wireframes

**Dashboard**

```
┌──────────────────────────────────────────────────────────────┐
│ AMAZI · RWB            {river icon} AMAZI      [district] [▣] [◍] │
├──────────┬───────────────────────────────────────────────────┤
│OPERATIONS│  ╔═ The Amazi Reservoir ═══════════════════════╗   │
│ ● Dashbrd│  ║ (◔) RESERVOIR DIAL   ┃ RIVERLINE ━━╦━━   AI WATCH│
│ ○ Map    │  ║ HEALTH 74.2%         ┃ ▸▸▸▸▸   (tributaries)  ⟐  │
│ ○ Points │  ╚═══════════════════════════════════════════════╝ │
│ ○ Predict│  ┌ Functional 161 · At Risk 41 · Non-Fun 18 · Rep 3 │
│ ○ Tasks  │  ├───────────────────────┬────────────────────────┤
│ ● Notif. │  │ HIGHEST RISK NOW       │ DISTRICT PULSE         │
│ADMIN.    │  │ 1 ▸WP-0091 82% Bugesera│  Bugesera  ▓▓▓░░ 68%   │
│ ○ Reports│  │ 2 ▸WP-0114 77% Kigali  │  Kigali    ▓▓░░░ 52%   │
│ ○ Distr. │  │ 3 ▸WP-0230 71% Nyagatare│  Nyagatare ▓▓░░░ 47%  │
│ ○ Techs. │  └───────────────────────┴────────────────────────┘
│SYSTEM    │   [┌─ TODAY'S TASKS ──────────┐ ┌─ MODEL STATUS ──┐]
│ ○ Users  │   │ #4 WP-0012 CRITICAL overdue│ │ ● ONLINE acc.70%│
│ ○ Audit  │   │ #7 WP-0055 high  today    │ │  ROC-AUC 0.77  │
│ ○ Model  │   └───────────────────────────┘ └─────────────────┘
└──────────┴───────────────────────────────────────────────────┘
```

**GIS Map**

```
┌──────────────────────────────────────────────────────────────┐
│ MAP  [Filter rail: status ▾ district ▾ min risk ▾ search ⦿]   │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │   ◦◦◦◦◦   ●○○      ┌── layer panel ──┐                │  │
│ │       ╭◉ cluster (9)│ ☑ Water points │  ▲ Legend       │  │
│ │   ◦◦      ●  ●      │ ☑ Districts    │  ┌────────────┐ │  │
│ │        ●            │ ☐ Risk heatmap │  │ ● functional│ │  │
│ │   ●●    ╰➤ routes   │ ☐ Rainfall     │  │ ◔ at risk   │ │  │
│ │  [popup: WP-0091 82% At Risk]        │  │ ◌ non-func  │ │  │
│ └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Prediction Center**

```
┌──────────────────────────────────────────────────────────────┐
│ PREDICTION CENTER   [water point ▾]  [⟳ PREDICT]             │
│ ┌ PICK AN ASSET ───────────────┐ ┌ PREDICTION ─────────────┐ │
│ │ searchable selector          │ │ (◔) RISK DIAL 76%       │ │
│ │ WP-0091 · Borehole · Bugesera│ │ STATUS  [At Risk]        │ │
│ └──────────────────────────────┘ │ CONFIDENCE  High         │ │
│                                  │ CONTRIBUTING FACTORS     │ │
│                                  │ ┌age ▲ population ▲ ...  │ │
│                                  │ └─────────────────────── │ │
└──────────────────────────────────────────────────────────────┘
```

**Water Point Detail**

```
┌──────────────────────────────────────────────────────────────┐
│ WP-0091  [At Risk · 82%]   [Open in Map]                     │
│ ┌ TELEMETRY ──────┐ ┌ LOCATION ────────┐ ┌ RISK FACTORS ──┐ │
│ │ ID  WP-0091     │ │ mini-map (pin)   │ │ age 24y  ▲▲    │ │
│ │ Type Borehole   │ │ sector/cell/...  │ │ rainfall 141mm │ │
│ │ District Bugesera│ └─────────────────┘ │ population 812 │ │
│ │ Pop. 812 · 2010 │ ┌ MAINTENANCE ────┐ │ tech encode ▲   │ │
│ └──────────────────┘ │ task history     │ └────────────────┘ │
│                      └─────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

---

# PHASE 3 — Self-Critique

A deliberate pass to kill every "template" instinct.

| Artifact I found in my first draft | Why it was generic | Replacement |
|---|---|---|
| A KPI row of 6 identical big-number cards | Every Bootstrap admin has it; the numbers don't tell you what to *do* | One **reservoir gauge** (health) + a risk-ranked action list — the dashboard now answers "which point first" |
| `#0EA5E9`-adjacent sky blue primary | Tailwind `sky`; reads "SaaS" | `#116A78` deep-river teal with green-tinted neutrals — an instrument palette, not a brand kit |
| Spinner loading indicator | Vendor-generic | **Droplet-fill** indicator |
| OSM tile default with round bubble markers | Default Leaflet tutorial output | Custom droplet `divIcon`s, clusters, filter rail, instrument legend, detail popups |
| Chart.js default colors | Library defaults | Domain palette bound to status semantics, blueprint plot style |
| "Smart Water" name + generic droplet | No identity | **AMAZI** — a named watershed interface with a contour-droplet mark |
| Circular gauge with a needle | Automotive dashboard cliché | **Reservoir water-level** dial — the needle is a waterline |
| Oversized hero cards with shadows | Dribbble habit | Flat `e-1` panels, 8px max radius, 4px input radius |
| Random violet accent for "AI" | Crypto/startup signal | AI shares the reservoir instrument color — AI *is* the water intelligence |

**Resulting rule:** if a component can be found in any random SaaS admin template, it must be either removed or re-made so it only makes sense on a water platform.

---

# PHASE 4 — Implementation Mapping

| Design System Item | Implementation |
|---|---|
| Tokens | CSS custom properties in `static/css/style.css` under `:root` + `body.theme-dark` |
| Typography | Barlow + Barlow Condensed + IBM Plex Mono (Google Fonts, CDN) |
| Signature element | `static/css/style.css` `.reservoir`, `.riverline`, `.ai-watch` + inline SVG in `dashboard/index.html` |
| Status chips | `.chip` + `.chip-{functional|at-risk|non-functional|under-repair|pending}` |
| Shell / nav | `templates/base.html` — brand bar + role-gated rail + content frame |
| Public landing | `templates/landing.html` + `app/__init__.py` `home` route (anonymous visitors) |
| Login | `templates/auth/login.html` — watershed split-screen with contour backdrop |
| Dashboard | `templates/dashboard/index.html` + `app/dashboard.py::_index_context` (reservoir gauge, riverline, AI watch, district pulse) |
| GIS | `templates/dashboard/map.html` + `static/js/dashboard.js` (droplet pins, clusters, district footprints, rainfall overlay) |
| Water points list / detail | `templates/dashboard/water_points.html`, `_water_points_table.html`, `water_point_detail.html` |
| Prediction Center | `templates/dashboard/predict.html` — risk dial + contributing factors via `risk_factors_for()` |
| Districts | `templates/dashboard/districts.html` + `dashboard.districts` route (sector breakdown) |
| Model & Settings | `templates/admin/model_performance.html` + `admin.model_performance` route (metrics, confusion matrix, feature weights, settings) |
| Reports | `templates/reports/*` — `index.html`, 5 report pages, `_filter_bar.html`, `_pagination.html`, `_export_buttons.html` + `reports.py` |
| Maintenance (Tasks) | `templates/tasks/list.html`, `detail.html`, `create.html`, `_task_form_fields.html` — workflow chips + audit trail |
| Notifications | `templates/notifications/list.html` — `alert-rail-list`, unread markers |
| User / Technician admin | `templates/admin/users.html`, `technicians.html` + `_create_technician_form.html` (create via overlay dialog, `create_modal_open` re-opens it) |
| Approve / reset password | `templates/admin/approve_user.html` (applicant telemetry), `reset_password.html` |
| Audit / report logs | `templates/admin/_audit_table.html`, `audit_logs.html`, `report_logs.html` |
| Admin dashboard | `templates/admin/dashboard.html` — KPI stat grid + audit panel |
| Auth (register / temp password) | `templates/auth/_auth_shell.html` macro + `register.html`, `change_temp_password.html` (watershed split, same as login) |
| Auth (settings / pending) | `templates/auth/settings.html` (panel-grouped forms), `pending_approval.html` (status panel), `privacy_policy.html` |
| Charts | `static/js/reports-charts.js` palette update |
| Defense document | this file |

**Regression fixes landed alongside the redesign:** the dashboard `dict()` on 3-tuples bug in `_index_context` (`app/dashboard.py`), the missing `admin.model_performance` route that broke every admin page's `url_for`, template nesting errors in `model_performance.html` / `districts.html`, legacy `.login-split` markup (`display:none` in new CSS) that blanked `register.html` / `change_temp_password.html`, the `pending_approval.html` content-block swallowed by the navbar-block override in `base.html`, and outdated "Smart Water"/Bugesera copy. Full suite: `66 passed`; smoke of 43 page renders across admin/manager/tech/temp roles all 200 or correct access-control responses (403 out-of-district, 302 manager-only).

---

*© Amazi — RWB Water Intelligence. Design rationale, tokens, and code share one vocabulary: the watershed.*

---
name: Culinary Economics
colors:
  surface: '#fbf9f6'
  surface-dim: '#dbdad7'
  surface-bright: '#fbf9f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f0'
  surface-container: '#efeeeb'
  surface-container-high: '#eae8e5'
  surface-container-highest: '#e4e2df'
  on-surface: '#1b1c1a'
  on-surface-variant: '#3f4948'
  inverse-surface: '#30312f'
  inverse-on-surface: '#f2f0ed'
  outline: '#6f7978'
  outline-variant: '#bfc8c8'
  surface-tint: '#216868'
  primary: '#004343'
  on-primary: '#ffffff'
  primary-container: '#0f5c5c'
  on-primary-container: '#90d2d1'
  inverse-primary: '#90d2d1'
  secondary: '#825500'
  on-secondary: '#ffffff'
  secondary-container: '#fdab12'
  on-secondary-container: '#684300'
  tertiary: '#5e2f16'
  on-tertiary: '#ffffff'
  tertiary-container: '#7a452a'
  on-tertiary-container: '#ffb693'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#aceeee'
  primary-fixed-dim: '#90d2d1'
  on-primary-fixed: '#002020'
  on-primary-fixed-variant: '#004f50'
  secondary-fixed: '#ffddb3'
  secondary-fixed-dim: '#ffb951'
  on-secondary-fixed: '#291800'
  on-secondary-fixed-variant: '#633f00'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb693'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#6c391f'
  background: '#fbf9f6'
  on-background: '#1b1c1a'
  surface-variant: '#e4e2df'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  currency-display:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system is crafted for independent restaurant and café operators in India—busy, pragmatic entrepreneurs who need financial transparency without balance-sheet jargon. The interface marries warm hospitality with decisive commercial precision. 

The aesthetic is grounded, warm, and highly structured, drawing from a tailored **Tactile Modernist** paradigm:
- **Atmospheric Warmth:** Surfaces reject clinical cold grays in favor of stone, warm milk, and linen tones, setting a calm operational baseline during hectic service hours.
- **Cognitive Ease:** Visuals strip away abstract financial acronyms, replacing them with clear, direct culinary terms and immediate operational feedback.
- **Pragmatic Utility:** High-density data matrices, recipe ingredient yields, and unit pricing are rendered with crisp contrast, ensuring glanceable readability under varied kitchen and back-office lighting.

## Colors

The palette establishes an authoritative, calm anchor through deep herbal teal, balanced by warm golden saffron for high-priority operational interactions. 

### Matrix Classification Quadrants
The system enforces strict, semantic color pairs (solid marker/border + pastel container) for classic menu engineering classifications:
- **Stars (High Profit, High Popularity):** Emerald Green (`#15803D`) on pale mint background (`#DCFCE7`).
- **Plowhorses (Low Profit, High Popularity):** Warm Amber (`#D97706`) on light buttercup background (`#FEF3C7`).
- **Puzzles (High Profit, Low Popularity):** Vibrant Blue (`#2563EB`) on soft azure background (`#DBEAFE`).
- **Dogs (Low Profit, Low Popularity):** Crimson Red (`#DC2626`) on soft blush background (`#FEE2E2`).

### Functional Distribution
- **Canvas Base:** Soft off-white linen (`#FAF8F5`) prevents eyestrain across sustained audit sessions.
- **Card & Table Elevated Surfaces:** Pure crisp white (`#FFFFFF`) to clearly demarcate actionable data boundaries.
- **Primary Teal (`#0F5C5C`):** Used strictly for core actions, persistent navigation states, and primary summary metrics.
- **Saffron Accent (`#F4A300`):** Reserved for contextual warnings, highlight cards, attention-required margins, and conversion moments.
- **Text & Structure Hierarchy:** Deep ink charcoal (`#1C2626`) for primary metrics and titles; muted botanical slate (`#536363`) for metadata, subheadings, and secondary labels; subtle oat border (`#EBE6DF`) for hairline table and panel dividers.

## Typography

The typographic engine relies entirely on **Inter**, configured for immediate parsing under time-constrained restaurant management conditions.

### Rupee Formatting & Numerical Legibility
- All Indian Rupee values must render the currency glyph (`₹`) using tabular figures (`font-variant-numeric: tabular-nums`) to ensure vertical column alignment across recipe breakdown rows.
- Currency symbols match the weight of the adjacent numeral rather than defaulting to generic symbol weights.
- Rupee metrics maintain bold (`700`) weights in dashboard overviews, with decimal fractions scaled to 80% opacity when presenting precision batch costing (e.g., `₹142.50` per portion).

### Content & Labeling Doctrine
- Avoid accounting terminology. Use "Ingredient Cost" rather than "COGS", "Cash Margin per Plate" instead of "Gross Contribution Margin", and "Total Sales Volume" instead of "Throughput Rate".
- Section titles and key performance indicators favor direct, imperative phrases.

## Layout & Spacing

The layout is built upon an 8pt base grid with a fluid 12-column master structure on desktop screens, consolidating to 6 columns on tablets and 4 columns on mobile viewports.

### Breakpoints & Canvas Flow
- **Desktop (1280px+):** Fixed collapsible navigation rail (260px) paired with a responsive 12-column layout. Margin set to `2rem`, gutters at `1.5rem`.
- **Tablet (768px – 1279px):** Adaptive 6-column matrix. Margin set to `1.5rem`, gutters at `1rem`. Secondary analytical panels collapse to bottom draw sheets.
- **Mobile (< 768px):** Single-column stacking with sticky bottom action tray. Horizontal margins contract to `1rem` to maximize table workspace for item calculations.

### Spacing Principles
- Complex tables (e.g., Recipe Ingredient Breakdown) utilize dense compact spacing (`space-sm` row padding) to allow 10+ ingredients within an immediate viewport without scrolling.
- Overview analytical cards enforce generous breathing room (`space-lg` internal inset) to keep high-stakes metrics isolated from dense transactional lists.

## Elevation & Depth

Visual hierarchy uses a soft, organic elevation system to reflect ambient room lighting rather than synthetic drop shadows. Surfaces appear slightly lifted above the linen canvas.

### Elevation Levels
- **Level 0 (Flat Canvas):** Off-white base (`#FAF8F5`). No shadow. Structural dividers rely on a 1px solid stroke (`#EBE6DF`).
- **Level 1 (Default Data Containers & Cards):** Pure white background (`#FFFFFF`) paired with an ambient shadow: `0 2px 8px -2px rgba(15, 92, 92, 0.05), 0 1px 3px 0 rgba(0, 0, 0, 0.03)` with a subtle outer border (`#ECE8E1`).
- **Level 2 (Interactive Floating Elements, Dropdowns, Hovered Cards):** Lifted state with `0 10px 24px -4px rgba(15, 92, 92, 0.08), 0 4px 8px -2px rgba(0, 0, 0, 0.04)`.
- **Level 3 (Modal Sheets, Recipe Detail Sliders):** High focus overlay using `0 20px 32px -6px rgba(15, 38, 38, 0.14), 0 8px 16px -4px rgba(0, 0, 0, 0.06)`, bounded by a dim canvas backdrop (`rgba(28, 38, 38, 0.4)`).

## Shapes

The design system embraces a friendly, non-industrial geometry that softens dense data presentation.

### Geometric Rules
- **Primary Content Cards & Dashboards:** Defined at a fixed `1rem` (16px, `rounded-2xl`) corner radius. This curved silhouette differentiates key analytical modules from cold spreadsheets.
- **Form Inputs, Buttons, & Table Headers:** Standardized at `0.5rem` (8px, `rounded-md`) to ensure sharp target definition without feeling overly rounded or imprecise.
- **Status Pills, Matrix Badges, & Rupee Tags:** Strict full pill geometry (`rounded-full`) to clearly distinguish classifications from operational buttons.

## Components

### Buttons
- **Primary Action (e.g., "Add Recipe", "Save Costing"):** Solid Deep Teal background (`#0F5C5C`), pure white text, 8px radius, medium weight (`600`). Hover elevates with a subtle brightness lift and soft teal shadow.
- **Secondary Action (e.g., "Export Menu PDF"):** Border 1.5px solid `#0F5C5C`, transparent background, `#0F5C5C` text.
- **High-Impact Saffron (e.g., "Optimize Pricing"):** Solid `#F4A300` background with deep slate text (`#1C2626`) for maximum visual urgency without resorting to error colors.

### Menu Matrix Badges
- Pill-shaped labels consisting of an inset 6px dot indicator alongside uppercase text.
- **Star:** `#DCFCE7` background, `#15803D` border/dot/text ("STAR").
- **Plowhorse:** `#FEF3C7` background, `#D97706` border/dot/text ("PLOWHORSE").
- **Puzzle:** `#DBEAFE` background, `#2563EB` border/dot/text ("PUZZLE").
- **Dog:** `#FEE2E2` background, `#DC2626` border/dot/text ("DOG").

### Recipe Ingredient Table
- **Layout:** High-density striped or thin-bordered table rows (`#EBE6DF`).
- **Columns:** Ingredient Name, Purchase Unit, Unit Cost, Raw Quantity, Yield Loss %, and Calculated Plate Cost.
- **Total Strip:** Prominent baseline summary row styled with an inset pale teal wash (`rgba(15, 92, 92, 0.04)`), featuring tabular bold rupee numbers (`currency-display`).

### Input Fields & Cost Controls
- Inputs use a pure white surface with a 1px border (`#D8D3CB`), shifting to a 2px `#0F5C5C` focus ring with zero vertical jitter.
- Numerical fields for currency must feature an immutable prefix icon/badge (`₹`) styled in muted slate.
- Unit toggle controls (e.g., kg / g / L / ml) sit anchored inside the right edge of the input box as a segmented selector.

### Profit & Cost Margin Sliders
- Interactive range controls for running hypothetical price adjustments ("What-If Price Simulator").
- Track finished in soft sand (`#E5E0D8`) with an active fill in `#0F5C5C`. Handle is a prominent 20px white disk with a subtle elevated ring shadow.
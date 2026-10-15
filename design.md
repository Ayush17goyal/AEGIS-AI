# AEGIS AI / AI Guard Design System

This document describes the current visual and interaction design of the AEGIS AI website as implemented in this repository. It is intended to be sufficient for rebuilding the interface in another React application, a static HTML/CSS implementation, or another frontend stack without needing to infer the visual language from screenshots alone.

The product has two connected surfaces:

1. A public, cinematic landing page that introduces the protection-first AI gateway.
2. An authenticated security workspace for chat, monitoring, analytics, policy management, document security, and evaluation.

The current frontend includes a readability pass that raises the base type to 15px and avoids using 7–10px text for important labels, metadata, tables, notices, or form controls. A subsequent global typography pass adds exactly 5px to every fixed-pixel `font-size` declaration in the frontend styles, including mobile rules. Fluid `clamp()` typography remains fluid.

The design principle is **intelligence without exposure**: an almost-black, warm charcoal base; amber/gold as the signal of trust and active protection; restrained glass and atmospheric photography; compact operational typography; and strong visual hierarchy without a generic SaaS-blue palette.

## Source of truth

Studio repair note (2026-10-15): the existing color tokens, card grid, sidebar and typography are preserved. Execution receipts now distinguish PASS/FAIL/ERROR/NOT IMPLEMENTED, show actual provenance, and label authorization-only verification separately. Missing approved model components are visible, historical excluded cards are disabled, and the six-step tour explains unavailable output verification. Mobile Studio/header wrapping was adjusted after a browser test found 30px overflow. Scope and implementation evidence live in `docs/STUDIO-AUDIT.md`, not in this visual reference.

The current implementation is in:

- `src/theme.css` — shared design tokens.
- `src/styles.css` — global reset, landing primitives, workspace components, responsive rules, and motion.
- `src/landing.css` — scoped cinematic landing overrides and hero atmosphere.
- `src/main.tsx` — page structure, routes, content, states, icons, charts, and interactions.
- `src/components/HeroVideo.tsx` and `src/components/heroMedia.ts` — optional hero-video discovery, fallback, and reduced-motion behavior.

The project uses React + TypeScript + Vite, Lucide React for icons, Recharts for data visualizations, and Tailwind CSS only as an imported build dependency. The visual system is primarily authored in regular CSS.

## Brand character

The interface should feel:

- Protective, precise, and technically credible.
- Premium but not glossy or luxurious.
- Warm, human, and atmospheric rather than cold cyberpunk.
- Quiet in its default state, with amber highlights appearing when something is active, trusted, selected, or actionable.
- Dense enough for an operations console, but with generous spacing around major headings and hero composition.

Avoid:

- Blue or purple “AI dashboard” defaults.
- Pure black and pure white as the dominant palette.
- Heavy gradients on every surface.
- Excessive rounded cards, playful illustrations, or loud neon effects.
- Overly bold or geometric type; the existing system uses light/regular weights and tracking to create authority.

## Color system

All major colors are CSS custom properties in `src/theme.css`.

| Token | Value | Use |
| --- | --- | --- |
| `--brand-bg` | `#100b07` | Main page/workspace background. Very dark warm brown. |
| `--brand-bg-secondary` | `#17100b` | Sidebar, inputs, secondary dark surfaces. |
| `--brand-surface` | `#211810` | Cards, panels, modal backgrounds. |
| `--brand-surface-hover` | `#2b1e13` | Hover and selected surface state. |
| `--brand-amber` | `#ffb547` | Primary accent, active borders, icons, status dots. |
| `--brand-gold` | `#ffd18a` | Softer highlight, key text, icon glow, CTA text contrast. |
| `--brand-copper` | `#c87524` | Deeper amber/copper accents and selection background. |
| `--brand-burnt-orange` | `#713c13` | Atmospheric glow, radial gradients, warm shadow color. |
| `--text-primary` | `#f5e9da` | Main text; warm cream rather than white. |
| `--text-secondary` | `#c4b09a` | Body copy and supporting labels. |
| `--text-muted` | `#93806d` | Metadata, captions, quiet secondary information. |
| `--border-subtle` | `rgba(255, 181, 71, 0.14)` | Default card and divider border. |
| `--border-active` | `rgba(255, 181, 71, 0.34)` | Hover/selected border. |
| `--amber-glow` | `rgba(255, 181, 71, 0.12)` | Soft amber shadow/glow. |
| `--status-success` | `#a8d5a0` | Healthy, allowed, online, pass. |
| `--status-warning` | `#ffb547` | Warning, approval, active amber state. |
| `--status-danger` | `#e87970` | Blocked, denied, error, failed. |
| `--status-info` | `#78c6bd` | Masked/redacted or informational state. |
| `--chart-sage` | `#b4c7a3` | Muted chart series. |
| `--chart-grid` | `rgba(255, 181, 71, 0.07)` | Chart grid lines. |

### Light theme

The frontend now supports a persistent light theme through the sun/moon toggle in the public header and authenticated workspace header. The preference is stored in `localStorage` under `aegis-theme` and applied to the document root as `data-theme="light"`.

The light theme preserves the AEGIS identity rather than switching to a generic blue/white dashboard:

- Page background becomes warm ivory: `#f5efe6`.
- Secondary surfaces become sand: `#eee5d8`.
- Cards become cream: `#fffaf2`.
- Text becomes dark warm brown: `#2a1c12`, with brown-beige secondary text.
- Amber/gold accents deepen to `#b86b16` and `#8f4d0b` for contrast on pale surfaces.
- Green, teal, and red status colors become darker, print-like variants.
- Workspace panels receive a very soft warm shadow to separate them from the ivory background.

The portrait-led hero remains an intentionally dark cinematic media stage in light mode so the source image, amber rim light, and cream hero copy retain contrast. The trust strip, platform section, feature rows, footer, workspace shell, forms, panels, tables, notices, and modals follow the light palette.

Feature Demo Studio also has explicit light-theme surfaces: talking-point panels use pale blue-gray with dark blue labels, payload areas use warm sand, sanitized previews use pale sage, and pass/error chips use darkened accessible status colors. Dark-theme demo blocks must not be reused unchanged in light mode because their original light text is designed for a dark background.

To reproduce the theme switcher, set `document.documentElement.dataset.theme` to either `dark` or `light`, define both token sets, and keep the icon-only control keyboard accessible with an `aria-label` describing the destination theme.

### Color behavior

- Default text is cream, not white.
- Body text is secondary warm beige; supporting text is muted brown-gray.
- Accent text is usually gold; active icons and small indicators are amber.
- Borders are thin and low-opacity. Use the border to define structure, not heavy shadows.
- Surface contrast is subtle: background → secondary background → surface → hover surface.
- Error styling is intentionally muted: `#ebb09f` text on a translucent burnt-red background, not a saturated red block.
- Selection uses copper: `background: var(--brand-copper); color: #fff`.

## Typography

The font stack is:

```css
font-family: Inter, Arial, sans-serif;
```

Inter is requested from the local system with a swap fallback. A practical reproduction should use Inter if available, then Arial/sans-serif.

### Type roles

| Role | Current treatment |
| --- | --- |
| Hero display | `clamp(52px, 5.25vw, 76px)` token; regular/400 weight; tight line-height around `1.04`; negative tracking around `-3px`. |
| Workspace page title | About `31px`, weight 400, letter-spacing `-1px`; mobile about `25px`. |
| Workspace panel title | About `14px`, weight 500; compact and practical. |
| Section kicker | 7–9px uppercase, amber/gold, letter-spacing `1.2–1.8px`. Format is often `01 / SECURITY OVERVIEW`. |
| Navigation | 10–12px, muted warm beige. |
| Body copy | 11–14px, line-height around `1.6–1.7`. |
| Metadata/table headers | 7–10px, uppercase, muted, letter-spacing `0.7px`. |
| IDs and event data | `Consolas`, monospace, slight positive tracking. |

Use sentence case for primary headings. Use uppercase only for kickers, labels, statuses, identifiers, and small navigation metadata.

## Global geometry

- `box-sizing: border-box` globally.
- Body margin is zero.
- The root uses dark color scheme and antialiased text.
- Links inherit color and have no underline by default.
- Buttons are borderless by default and inherit the surrounding font.
- `border-radius` is restrained: 4–7px for controls, 7–12px for cards, 15–16px only for large hero/modal shapes.
- Standard card border is one pixel.
- `html { scroll-behavior: smooth; }`, except reduced-motion users.
- Main landing max width is about 1600px with fluid horizontal padding.
- Workspace content max width is 1500px and centered inside the area to the right of the sidebar.

## Logo and brand mark

The brand is text-led: `AEGIS AI`, with a shield mark in a warm amber outline.

- Landing header logo uses the cropped image in `.brand-mark` (`/ai-guard-logo-transparent.png` or the configured brand asset) inside a 48×40px clipped region.
- Workspace sidebar uses the same brand component but hides the small tagline and divider.
- Brand name is around 21–22px on desktop and 20px on small screens.
- The secondary product line is small, uppercase, muted, and letter-spaced: `INTELLIGENCE. PROTECTED.`
- The shield icon is typically a Lucide `Shield`/`ShieldCheck` icon with an amber border/glow.

## Public landing page

### Page composition

The landing page is a full-width cinematic composition with a maximum content width around 1600px:

1. Transparent public header.
2. Hero scene with image/video background, left-aligned manifesto copy, right-side operational cards, and bottom status rail.
3. Trust strip with three protection claims.
4. Platform introduction section.
5. Three feature columns on desktop, stacked feature rows on mobile.
6. Minimal footer.

The root landing wrapper is `.cinematic-landing`, which isolates the background effects and uses a full-width warm charcoal base.

### Header

Desktop header:

- Height about 84px in the cinematic variant.
- Brand on the left.
- Three text links in the center/right: Platform, How it works, Protection.
- Outline CTA on the far right: `Open workspace ↗`.
- Horizontal padding is fluid: `clamp(28px, 5.8vw, 96px)`.

Mobile header:

- Height grows to about 100px because the nav becomes a second centered row.
- Brand and outline CTA remain on the first row.
- The nav remains visible in the cinematic version at widths up to 760px, centered with roughly 30px gaps. The older generic landing rules hide nav below 700px; preserve the cinematic override when reproducing the current page.

### Hero scene

The hero is not a conventional card. In the cinematic variant it is transparent and blends into the page atmosphere:

- Desktop height: about 630px, rising to 680px on very wide screens.
- No visible outer border or card shadow in the current cinematic variant.
- Background image: `/aegis-hero.webp` desktop and `/aegis-hero-mobile.webp` mobile.
- The image is placed in `.scene-image`, with a dark left-to-right overlay, a bottom fade/mask, and slow camera drift.
- `scene-light` adds radial amber highlights around the face and lower scene.
- `scene-haze` uses `/amber-haze.svg`, screen-blended and masked, to create a soft copper haze below the portrait.

The hero copy is placed in the left 45% of the desktop composition, beginning around 106–110px from the top. The primary headline is:

```text
INTELLIGENCE.
  WITHOUT
EXPOSURE.
```

The first two lines are cream. `EXPOSURE.` uses an amber-to-gold text gradient. The middle line is visually indented by about 8% on desktop. On mobile the indent is removed.

The paragraph is short, warm cream, and constrained to roughly 230–310px. The main CTA is a filled amber gradient button: `Enter secure workspace ↗`.

Below the CTA is a small product statement with an amber pixel-stack glyph and a kicker:

```text
BUILT FOR THE NEXT ERA OF AI
Your data stays yours. Inspect every prompt, stop leaks before they happen, and let your team work with AI confidently.
```

### Hero telemetry cards

The desktop hero has a narrow right-side stack, visually integrated into the image rather than rendered as opaque cards. The cards are:

- **Gateway status**: shield icon with orbital rings, online dot, short copy, and animated signal bars.
- **Protection pipeline**: large circular `03` indicator, `IN` and `OUT` chips, and `Inspect / Enforce / Protect` labels.
- **Model independence**: compact response strip stating it works with any LLM or private model.

The cards use `.glass` as a structural class, but the cinematic override makes them transparent, removes the border/backdrop blur, and relies on typography, rules, orbits, and glow for separation.

The hero also includes:

- A small top-left eyebrow: `AI SECURITY, REIMAGINED.`
- Top-right index: `AEGIS / 001`.
- A circular bottom seal: `PREVENTION FIRST` (hidden on smaller screens).
- Bottom status rail: `BUILT FOR THE NEXT ERA OF AI` on the left and `EXPLORE THE PLATFORM ↗` on the right.
- A small circular motion-control button for explicit pause/play.

### Trust strip

The strip is a thin horizontal divider region, around 64px high on desktop. It includes:

- `LESS EXPOSURE. MORE POSSIBILITY.`
- `Input inspection`
- `Authorized retrieval`
- `Output protection`
- `ONE CONNECTED GATEWAY ↗`

Use small Lucide icons, muted cream text, amber icon strokes, and no filled cards.

### Platform section

The section begins with `01 / THE PLATFORM`, then a two-column intro:

- Left: large heading, roughly 34px: `Give intelligence / a secure boundary.`
- Right: supporting copy, around 390px wide.

The three features are:

1. **Your information, shielded.** — detect personal identifiers, financial details, and secrets; mask sensitive values before model access.
2. **Instructions stay in control.** — inspect direct and document-based injection attempts; block risky requests before model invocation.
3. **Access is always earned.** — retrieve documents only after server-side permission checks; keep restricted context behind its boundary.

Each feature has a left amber rule, a Lucide icon, a `01/02/03` marker, short description, and `Explore protection ↗` text button. On hover the left rule brightens and a subtle copper-to-transparent wash appears.

### Landing footer

Use a top divider, the compact AEGIS AI lockup, a tiny tagline, a synthetic-demo note, and `Back to top ↑`. Keep it quiet and low-contrast.

## Authenticated workspace

### Shell

The workspace is a fixed-sidebar application shell:

- Sidebar: 225px desktop width, dark secondary background, fixed to the left, full viewport height.
- Main area: `margin-left: 225px`, width `calc(100% - 225px)`.
- Header: 69px high, bottom border, breadcrumb/status context on the left and offline/private session indicators on the right.
- Content: max width 1500px, around 36px top and 34px horizontal padding.
- Footer: thin top border, small privacy/deployment metadata.

The main background has a subtle radial burnt-orange glow behind the upper content. It should be almost imperceptible until viewed against the dark surface.

### Sidebar

Sidebar order:

1. AEGIS AI brand.
2. `SECURITY WORKSPACE` label and `LOCAL` badge.
3. Navigation.
4. Bottom protection note.
5. Current-user block.

Navigation entries and routes:

| Label | Route | Icon |
| --- | --- | --- |
| Overview | `/app` | grid/layout |
| Secure chat | `/app/chat` | message square |
| Live monitor | `/app/monitor` | activity pulse |
| Analytics | `/app/analytics` | chart |
| Policies | `/app/policies` | sliders/settings |
| Document security | `/app/documents` | locked file |
| Evaluation | `/app/evaluation` | flask |

Navigation rows are about 12px text with 12–13px vertical/horizontal padding and 7px radius. Icons are amber. The active row has:

- `var(--brand-surface-hover)` background.
- `var(--border-active)` border.
- Gold text.
- A 3px amber inset bar on the left.
- A right chevron revealed only for the active state.

The bottom protection note is a bordered surface with shield icon and `Prevention first / Input. Context. Output.` The user row has a gold circular avatar, name, role, and logout icon.

### Page header

Every workspace route uses the same `PageHead` pattern:

- Small numbered kicker.
- 31px regular-weight title.
- One-sentence muted description.
- Optional action button aligned right.

Examples:

- `01 / SECURITY OVERVIEW` — `Intelligence, protected.`
- `02 / AI SECURE CHAT` — `Ideas in. Exposure out.`
- `03 / LIVE SECURITY MONITOR` — `Every decision. Visible.`
- `04 / DATA LEAKAGE ANALYTICS` — `See the bigger picture.`
- `05 / POLICY MANAGEMENT` — `Protection, on your terms.`
- `06 / DOCUMENT SECURITY` — `Knowledge with boundaries.`
- `07 / EVALUATION & BENCHMARKING` — `Evidence over assumptions.`

### Workspace primitives

#### Buttons

Primary button:

- Filled diagonal gradient from `#ffd18a` to `#ffb547`.
- Dark brown text.
- 7px radius.
- 12px-ish text, medium/semibold weight.
- Amber glow shadow.
- Usually paired with a Lucide icon on the right.

Outline button:

- Transparent or nearly transparent background.
- One-pixel active amber border.
- 7–8px radius.
- Warm cream text.
- Hover fills with `var(--brand-surface-hover)` and brightens the border.

Text button:

- No box or fill.
- Amber/gold text and an arrow icon.
- Used for low-emphasis actions such as `Explore protection`, `Edit access`, and `View all`.

#### Panels and metrics

`.panel` is the primary workspace container:

```css
border: 1px solid var(--border-subtle);
background: var(--brand-surface);
border-radius: 11px;
padding: 22px;
margin-bottom: 22px;
```

Metric cards use the same surface and border language, with 10px radius and around 20px padding. A label and icon sit at the top, a large regular-weight value in the middle, and a muted explanation below. Four metrics are used on wide desktop layouts.

#### Notices and errors

- `.notice`: quiet bordered row, translucent neutral fill, 10px text, icon at left, around 13px × 16px padding.
- `.error`: muted brick-red surface and border; 11px text; use for actionable errors.
- Keep notices informative rather than attention-seeking.

#### Badges

Small uppercase-ish status badges use a 4px radius, one-pixel border, and 5px × 7px padding.

- Safe/allow/pass: sage green.
- Warning/approval: amber/gold.
- Danger/block/deny/fail: dusty red.
- Mask/redact: teal.
- `ACCESS DENY` uses a dashed border.
- `REQUIRE APPROVAL` uses the gold/amber treatment.

#### Tables

- Full-width, collapsed borders, 10px body text.
- Table headers are 8px uppercase with tracking and muted color.
- Row padding is around 16px × 12px.
- Each row has a subtle bottom border.
- Hover uses the hover surface and indicates that the row is interactive.
- Long tables live inside `.table-scroll` with horizontal overflow.
- Incident IDs use the monospace class.

## Workspace route patterns

### Overview

The overview starts with an image-backed banner using the hero portrait, dark left gradient, and a shield mark on the right. Below it:

1. Four metric cards.
2. Two-column gateway activity and protection breakdown charts.
3. Full-width recent security events table.
4. Four compact footer metrics.

The banner uses the same visual language as the landing hero, but in a restrained operational crop: minimum height around 242px, 12px radius, `aegis-hero.webp` centered around 43%.

### Secure chat

Desktop layout is a large chat panel plus a 280px aside. The chat panel is a tall bordered surface with:

- Header showing secure status.
- Welcome state with shield illustration and sample prompts.
- User bubbles and assistant evidence bubbles.
- Inspection/enforcement status row with a spinning refresh icon while processing.
- Composer at the bottom with send action.

The aside contains “Try the security boundary” demo prompt cards and an enforcement pipeline. At widths below 950px, the aside moves below the main chat; below 700px the pipeline is hidden to preserve focus.

### Live monitor

Use filter controls above a full event table. Search and select fields use the standard dark input, subtle amber border, 6px radius, and 11px text. Risk uses a numeric value plus a short horizontal bar, colored according to severity.

### Analytics

Use four metric cards, then responsive chart panels in two-column groups. Donut legends use tiny colored dots, 8px labels, and right-aligned counts. Charts should use dark transparent backgrounds, amber/sage/teal/dusty-red series, and very subtle amber grid lines.

### Policies

Policy cards are flexible rows containing:

- Shield icon.
- Policy ID/category and description.
- Threshold input.
- Action select.
- Scope select.
- Enable toggle.
- Save outline button.

Below the cards, show mandatory controls as icon/text rows and a human review queue. On mobile policy cards wrap; fields shrink to around 110px selects and the save action moves to the right.

### Document security

Documents are presented in a responsive card grid. Each card contains a locked-file icon, classification badge, title, source/id, ownership detail list, retrieval test action, and optional access-edit action. The add/edit flow is a centered modal with a darkened blurred overlay and a stacked form.

The form communicates privacy explicitly: ownership is assigned server-side, permissions are checked before retrieval, and public documents are visible to authenticated users.

### Evaluation

The evaluation page starts with a notice describing the synthetic test suite, then metric cards, a confusion-matrix panel, prevention outcomes panel, and a horizontally scrollable evaluation table. It is intentionally evidence-oriented: labels should mention synthetic fixtures and limitations rather than imply general-world accuracy.

## Modal and authentication design

The modal system uses:

- Fixed full-screen overlay.
- `#0a0908c9` translucent backdrop.
- `backdrop-filter: blur(8px)`.
- Centered surface with 15px radius, subtle amber border, and deep shadow.
- 24px outer padding on small screens; about 34px on standard modals.

The login modal is a multi-step onboarding flow:

1. Choose Individual or Company.
2. If Company, choose a role.
3. Sign in.

The progress indicator uses muted labels, with the current step in gold and an amber underline. Choices are full-width dark rows with icon, title, description, and chevron. Hover/focus changes the border to amber and surface to `var(--brand-surface-hover)`. The password field has an in-field visibility toggle.

The current demo flow is part of the product UX and should be retained if rebuilding the demo: account selection filters demo identity, but does not grant permissions; backend identity and role remain authoritative.

## Responsive behavior

Breakpoints currently used:

| Breakpoint | Behavior |
| --- | --- |
| `min-width: 1500px` | Hero copy moves down slightly; hero cards grow; seal moves farther right/down. |
| `max-width: 1200px` | Landing padding tightens; hero title and cards shrink; workspace content padding reduces; document grid becomes two columns. |
| `max-width: 1100px` | Cinematic hero compresses to about 600px; cards narrow; scene crop shifts; feature spacing tightens. |
| `max-width: 950px` | Workspace sidebar narrows to 190px; metrics become 2 columns; chat aside moves below; documents become one column. |
| `max-width: 760px` | Cinematic landing becomes a flowing vertical composition; hero cards move below the copy; scene uses mobile portrait; feature grid stacks. |
| `max-width: 700px` | Public nav hides in the generic landing rules; workspace sidebar becomes an off-canvas menu; main area becomes full width; panels and headings shrink. |
| `max-width: 400px` | Hero type reduces to about 37px; response card stacks internally; horizontal padding becomes 20px. |

Mobile principles:

- Preserve the image and amber atmosphere, but let the composition flow vertically.
- Keep the headline and CTA above the operational cards.
- Replace fixed sidebar with a hamburger-triggered drawer.
- Reduce content padding to 17–20px.
- Stack two-column dashboard content.
- Retain readable status labels and controls; reduce decoration before reducing usability.

## Motion and media behavior

The design uses motion as ambient depth, not as navigation:

- `scene-drift`: slow background scale/vertical shift.
- `portrait-drift`: subtle hero image camera movement, with pointer offsets via `--pointer-x`/`--pointer-y`.
- `ambient-light`: slow radial glow movement.
- `panel-float`: 8px vertical float for hero panels/seal.
- `orbit-forward` and `orbit-backward`: rotating shield orbit rings.
- `signal-wave`: animated telemetry bars.
- `amber-breathe`: pulsing flow-ring glow.
- `title-reveal`: fade, upward movement, and blur removal on hero copy.
- `section-reveal`: scroll-linked entrance where supported.

The hero has an explicit pause/play button. Applying `.motion-paused` pauses hero scene animations. The implementation also respects `prefers-reduced-motion: reduce` by disabling most animations and smooth scrolling. The optional hero video is only used when:

- The user has not requested reduced motion, unless explicitly overridden.
- Data Saver is not active.
- The connection is not detected as 2G.
- A supported WebM/MP4 source is found in `/videos/hero-media.json` and passes a HEAD/content-type check.
- Playback succeeds.

If any check fails, the static WebP poster remains visible. Never make the hero depend on video to communicate the product.

## Icons and illustration language

Use Lucide React icons with thin strokes and modest sizes. Common visual motifs:

- Shield / shield-check: trust, gateway, protection.
- Lock / locked file: private access and document boundaries.
- Activity / chart / flask: telemetry and evidence.
- Sliders: policy control.
- Arrow-up-right: forward action and exploration.
- Check / X: pass, approve, reject.

Do not add filled emoji-like iconography. Icons should generally be amber/gold inside the public surface and amber/cream inside workspace surfaces.

## Interaction and accessibility requirements

- All interactive controls use native buttons, links, labels, inputs, selects, and textareas where possible.
- `:focus-visible` is a 2px amber outline with 4px offset.
- Disabled buttons reduce opacity to 0.45 and show a wait cursor.
- Icon-only controls need an accessible label, especially close, logout, menu, motion, and password visibility controls.
- Status dots and badges should not be the only carrier of meaning; pair color with text.
- Respect reduced motion and visibility changes; pause video when the document is hidden.
- Keep tables horizontally scrollable on small screens rather than forcing unreadable columns.
- Preserve warm text contrast against the dark surfaces.

## Reproduction recipe

To recreate the current design in another frontend:

1. Define the color tokens exactly as listed above and set the root background to `#100b07`.
2. Use Inter/Arial with a 14px base size, antialiasing, warm cream text, and 1.6–1.7 line-height for body copy.
3. Build a reusable brand component, primary/outline/text buttons, kicker, panel, metric card, badge, notice, modal, and table primitives.
4. Create a public shell with a transparent header, hero scene layers, left manifesto copy, right telemetry cards, trust strip, feature section, and minimal footer.
5. Use the supplied hero assets and preserve the left-dark/right-amber composition. Apply a dark gradient over the portrait so text remains readable.
6. Create a fixed 225px sidebar workspace shell with a 69px header and 1500px content max-width.
7. Use the seven routes and page-heading patterns listed above.
8. Use thin amber-tinted borders and moderate 7–12px radii for all operational surfaces.
9. Use regular-weight headings and small uppercase kickers to create hierarchy; avoid heavy bold typography.
10. Implement responsive changes at the listed breakpoints, especially the mobile hero reflow and off-canvas workspace sidebar.
11. Add the ambient motion only after the static layout is correct, then add the pause/reduced-motion/video fallback behavior.
12. Verify against the saved references in `docs/screenshots/landing.png`, `docs/screenshots/workspace-amber-desktop.png`, and `docs/screenshots/seamless-mobile.png`.

## Current asset map

| Asset | Role |
| --- | --- |
| `/aegis-hero.webp` | Desktop hero/poster image. |
| `/aegis-hero-mobile.webp` | Mobile hero/poster crop. |
| `/aegis-hero.png` | Alternate raster hero used by older/general hero rules. |
| `/ai-guard-logo-transparent.png` | Login/brand logo. |
| `/amber-haze.svg` | Warm atmospheric lower-scene overlay. |
| `/hero-video-mask.svg` | Mask that shapes optional hero video. |
| `/videos/hero-media.json` | Ordered desktop/mobile video source manifest. |
| `/videos/aegis-hero.webm` and `.mp4` | Desktop motion sources. |
| `/videos/aegis-hero-mobile.webm` and `.mp4` | Mobile motion sources. |

## Visual QA checklist

Before considering a reproduction complete, check:

- The page reads as warm charcoal/amber, not black/orange neon.
- The hero headline is the dominant element and the portrait remains visible behind/right of it.
- The left hero copy stays readable over the image.
- Telemetry cards align as a narrow right stack on desktop and become a two-column flow on mobile.
- The workspace sidebar remains visually distinct from the main surface.
- Active navigation has the amber inset bar and gold text.
- Panels have low-contrast borders, not heavy shadows.
- Metric cards, badges, tables, and notices share the same surface language.
- Mobile content does not overflow horizontally except inside intentionally scrollable tables.
- Motion pauses cleanly, reduced-motion mode remains usable, and static hero imagery works without video.
- Focus states are visible and all icon-only actions are labeled.

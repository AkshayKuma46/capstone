# AI Wardrobe Stylist — UX Specification
# For UX Designer / Frontend Team
# Interactions, flows, animations, micro-interactions, accessibility

---

## Core UX Principles

Before designing anything, understand these four principles. Every decision must serve them.

**1. Invisible AI**
The user should never feel like they are operating a machine. The AI happens silently behind a clean interface. No jargon, no model names, no confidence percentages in the user's face unless necessary.

**2. One action at a time**
Every screen has one primary action. The user is never overwhelmed with choices. Upload → Review → Save. Pick occasion → See outfits. Simple linear flows.

**3. Trust through transparency**
When the AI is uncertain, we say so — but gently. Not "confidence score 0.43" — instead "We're not sure about the fabric. Does this look right?"

**4. Reward the wardrobe**
Every garment the user adds should feel like a small win. The app grows with them. Animations and counts reinforce that their wardrobe is building.

---

## User Flows

### Flow 1 — First Time User (New Wardrobe)

```
Open app
    │
    ▼
Onboarding screen
    │
    ├── [Upload Photo] ──────────────────────────────────────┐
    │                                                         │
    └── [Skip] → Empty wardrobe screen                       │
                      │                                       ▼
                      └── [+ Add] ──────────────► Upload screen
                                                       │
                                                       ▼
                                               Photo selected
                                                       │
                                                       ▼
                                           AI processing (2-5s)
                                                       │
                                                       ▼
                                        Review attributes screen
                                                       │
                                         ┌─────────────┴──────────────┐
                                         ▼                             ▼
                                    [Edit fields]               [Save as is]
                                         │                             │
                                         └──────────────┬─────────────┘
                                                        ▼
                                              Saved ✓ → Back to wardrobe
                                              Wardrobe count: 1
```

### Flow 2 — Returning User (Get Outfit Recommendation)

```
Open app → Wardrobe (home)
    │
    ▼
Tap [Recommend] in bottom nav
    │
    ▼
Occasion selector
    │
    ▼
Tap occasion tile (e.g. Office)
    │
    ▼
Loading state (1-3s)
    │
    ▼
3 outfit cards shown
    │
    ├── Browse cards
    │
    ├── Tap card → expanded view
    │
    └── [Save to Collection]
              │
              ▼
         Name modal → Save → Toast ✓
```

### Flow 3 — Edit a Garment

```
Wardrobe grid
    │
    ▼
Tap garment card
    │
    ▼
Garment detail page
    │
    ▼
Tap [Edit]
    │
    ▼
All fields become editable dropdowns
    │
    ├── Make changes
    │
    └── [Save Changes]
              │
              ▼
         Saved ✓ → Back to detail view
         (embedding updates silently in background)
```

### Flow 4 — Delete a Garment

```
Garment detail page
    │
    ▼
Tap [🗑️]
    │
    ▼
Confirmation bottom sheet:
"Delete Navy Blazer? This cannot be undone."
[Cancel]  [Delete]
    │
    ▼
Tap [Delete]
    │
    ▼
Garment disappears with fade-out animation
Wardrobe count decreases by 1
Toast: "Navy Blazer removed"
```

---

## Interaction Design

### Tap Targets
- Minimum tap target size: 44×44px (Apple HIG standard)
- All buttons minimum height: 48px on mobile
- Bottom nav icons: 56px tall tap area
- Card taps: entire card is tappable, not just the text

### Gestures
| Gesture | Where | Action |
|---------|-------|--------|
| Tap | Garment card | Open detail |
| Long press | Garment card | Quick action sheet (Edit / Delete) |
| Swipe left | Garment card in grid | Reveal delete button |
| Pull down | Any list page | Refresh |
| Swipe down | Modal / bottom sheet | Dismiss |
| Tap outside | Modal | Dismiss (except destructive actions) |

### Transitions
| Transition | Type | Duration |
|-----------|------|---------|
| Page navigation | Slide right (push) | 300ms ease |
| Back navigation | Slide left (pop) | 250ms ease |
| Modal open | Slide up from bottom | 350ms ease-out |
| Modal close | Slide down | 250ms ease-in |
| Tab switch | Crossfade | 200ms |
| Card appear | Fade + slide up | 250ms staggered |
| Toast appear | Slide up from bottom | 200ms |
| Toast dismiss | Fade out | 150ms |

---

## Micro-Interactions

### Upload Button
- Default: dashed border, camera icon centered
- Hover/focus: border turns solid, background lightens
- Drag over: border pulses, background color changes to primary tint
- File dropped: brief bounce animation on the preview image appearing

### Garment Card
- Default: flat card, slight shadow
- Hover (desktop): card lifts — shadow deepens, scale 1.02
- Tap (mobile): brief scale down to 0.97 then back (spring physics)
- Long press: card scales to 0.95, action sheet slides up

### Occasion Tile (Recommend page)
- Default: rounded card with icon + label
- Tap: immediate scale to 0.93 then snap back, border highlights
- Selected: filled background, white text, checkmark appears
- After tap: tiles fade out, loading state fades in

### Score Bar (Outfit Card)
- Animates from 0% to final score when card appears
- Duration: 600ms, ease-out cubic
- Color: green (75+), yellow (50-74), red (<50)
- Score number counts up from 0 to final value simultaneously

### Save Button (Heart icon)
- Default: outline heart
- Tap: heart fills with bounce animation (scale 1.3 → 1.0)
- Saved state: filled heart, cannot be un-saved
- Haptic feedback on mobile (if available)

### Low Confidence Badge
- Appears as a subtle pulsing yellow dot next to the field label
- Tooltip on tap: "Our AI wasn't certain about this. Please check."
- Does not block the user — just informs

### Wardrobe Count
- When a garment is added → counter increments with a brief bounce
- When deleted → decrements with a brief shake animation

---

## States — Every Component Needs These

### Button States
| State | Visual |
|-------|--------|
| Default | Primary color, white text |
| Hover | Slightly lighter background |
| Active/Pressed | Slightly darker background |
| Disabled | 40% opacity, not clickable |
| Loading | Spinner replaces text, disabled |

### Input Field States
| State | Visual |
|-------|--------|
| Default | Gray border |
| Focus | Primary color border, slight glow |
| Filled | Dark border |
| Error | Red border, red error text below |
| Disabled | Light gray background, no interaction |

### Card States
| State | Visual |
|-------|--------|
| Default | Flat, subtle border |
| Hover | Elevated shadow |
| Selected | Primary color border |
| Disabled | Reduced opacity |

---

## Error Handling UX

### Rule: Never use a generic error message.
Every error tells the user exactly what went wrong and what to do next.

| Error | Message shown | Action offered |
|-------|--------------|----------------|
| File too large | "This file is too big (max 5 MB). Try compressing or choosing another photo." | Try again button |
| Wrong file type | "Only JPEG and PNG photos are accepted." | Try again button |
| AI analysis failed | "We couldn't analyse this photo. You can enter details manually instead." | Manual entry button |
| No network | "No internet connection. Check your connection and try again." | Retry button |
| Scoring failed | "We couldn't score outfits right now. Try again in a moment." | Retry button |
| Empty wardrobe + recommend | "Add some clothes to your wardrobe first, then we can find outfits for you." | Add garments button |
| Save failed | "Couldn't save this outfit. Please try again." | Retry button |

### Error placement rules
- Form field errors: directly below the field, red text, small font
- Page-level errors: centered on page, with icon and action button
- API errors: toast notification (bottom center)
- Critical errors (app broken): full screen error state with retry

---

## Loading States

### Rule: Never show a blank screen. Show a skeleton.

### Garment Grid Loading
```
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│▓▓▓▓▓▓▓▓│  │▓▓▓▓▓▓▓▓│  │▓▓▓▓▓▓▓▓│  │▓▓▓▓▓▓▓▓│
│▓▓▓▓▓▓▓▓│  │▓▓▓▓▓▓▓▓│  │▓▓▓▓▓▓▓▓│  │▓▓▓▓▓▓▓▓│
│▓▓▓▓    │  │▓▓▓▓    │  │▓▓▓▓    │  │▓▓▓▓    │
│▓▓      │  │▓▓      │  │▓▓      │  │▓▓      │
└────────┘  └────────┘  └────────┘  └────────┘
```
Shimmer animation sweeps left to right across all cards simultaneously.

### AI Processing Loading (Upload)
```
[Photo preview visible]

Analysing garment...      ████████████░░░░  75%

Identifying garment type ✓
Detecting colors...
```
Show progress steps checking off as they complete. Makes the wait feel active.

### Outfit Recommendation Loading
```
Finding outfits for Office...

[Shimmer card 1]
[Shimmer card 2]
[Shimmer card 3]
```
Show 3 skeleton cards immediately — sets expectation that 3 results are coming.

---

## Empty States

### Rule: Every empty state must explain WHY it's empty and offer ONE clear next action.

| Page | Empty state message | Action button |
|------|--------------------|--------------:|
| Wardrobe | "Your wardrobe is empty. Upload your first garment to get outfit ideas." | Upload a Garment |
| Collections | "No saved outfits yet. Find an outfit you love and save it here." | Find Outfits |
| Recommend (no match) | "No outfits found for this occasion. Try adding more clothes or choosing a different occasion." | Add Garments / Change Occasion |
| Collection detail | "This collection is empty." | Find Outfits |

---

## Feedback & Confirmation

### After every user action — confirm it worked.

| Action | Confirmation |
|--------|-------------|
| Upload garment | Toast: "Navy Blazer added to wardrobe ✓" |
| Edit garment | Toast: "Changes saved ✓" |
| Delete garment | Toast: "Navy Blazer removed" (no undo — brief 3s window would be better but not required) |
| Save outfit | Toast: "Saved to [Collection Name] ✓" |
| Delete collection | Toast: "Collection deleted" |
| Rename collection | Toast: "Renamed ✓" |

### Destructive action pattern
**Always use a two-step confirmation for delete:**
1. User taps delete icon
2. Bottom sheet appears with: garment name, warning text, [Cancel] [Delete]
3. [Delete] is red — visually communicates danger
4. [Cancel] is prominent — easy to escape

---

## Accessibility

### Text
- Minimum body text size: 14px
- Minimum label text size: 12px
- Never use text smaller than 12px
- Line height minimum: 1.4
- Do not rely on color alone to communicate meaning (always pair with icon or text)

### Contrast
- Body text on background: minimum 4.5:1 contrast ratio (WCAG AA)
- Large text / icons: minimum 3:1 contrast ratio
- Low confidence badge: yellow background must have dark text — check contrast

### Screen Readers
- All images must have descriptive `alt` text:
  - Garment photo: `alt="User uploaded photo of Navy Blazer"`
  - Occasion tile: `alt="Office occasion"`
  - Score bar: `aria-label="Compatibility score: 87 out of 100"`
- All interactive elements must have `aria-label` if icon-only
- Bottom nav tabs: `role="tab"`, `aria-selected="true/false"`
- Modal: `role="dialog"`, `aria-modal="true"`, focus trapped inside
- Toast: `role="alert"` so screen readers announce it immediately

### Keyboard Navigation (Desktop)
- All interactive elements reachable via Tab key
- Logical tab order: top-left to bottom-right
- Modal focus trap: Tab cycles only within modal
- Escape key closes modals and bottom sheets
- Enter/Space activates buttons and links

### Motion
- Respect `prefers-reduced-motion` media query
- If reduced motion is on: disable all transitions except simple fades
- Never use flashing or rapidly alternating animations

### Touch Accessibility
- Minimum touch target: 44×44px
- Adequate spacing between touch targets: minimum 8px gap
- Swipe gestures must have tap alternatives (don't rely only on swipe)

---

## Typography Scale

| Level | Size | Weight | Use |
|-------|------|--------|-----|
| Display | 28px | 700 | Page titles |
| Heading 1 | 22px | 700 | Section headers |
| Heading 2 | 18px | 600 | Card titles |
| Heading 3 | 16px | 600 | Sub-headers |
| Body | 14px | 400 | Regular content |
| Label | 12px | 500 | Form labels, metadata |
| Caption | 11px | 400 | Helper text, timestamps |

---

## Spacing System

Use a base-8 spacing scale:
- 4px — tight (icon padding, small gaps)
- 8px — small (between related elements)
- 16px — medium (card padding, section gaps)
- 24px — large (between sections)
- 32px — extra large (page padding)
- 48px — section (major separations)

---

## Navigation UX Rules

### Bottom Navigation (Mobile)
- Always visible — never hidden
- 3 tabs maximum: Wardrobe / Recommend / Collections
- Active tab: filled icon + primary color + label
- Inactive tab: outline icon + muted color + label
- Tapping active tab: scrolls to top of current page

### Back Navigation
- Always show a back arrow when the user is not on a root page
- Back arrow goes to the previous screen (not always the root)
- Never use "Cancel" for navigation — use "← Back" or "✕ Close"

### Breadcrumbs (Desktop only)
- Show on garment detail and collection detail pages
- Format: `Wardrobe > Navy Blazer`
- Each crumb is tappable

---

## Onboarding UX Notes

### First-time experience goals
1. User understands what the app does in 5 seconds
2. User adds at least one garment before leaving
3. No registration required (one user, local/session)

### Progressive disclosure
- Do not show all features at once
- First session: only show wardrobe upload
- After 3+ garments: surface the Recommend tab with a badge/dot
- After first recommendation: surface Collections

### Tooltip hints (one-time only)
- After first garment added: small tooltip on Recommend tab "Now find outfits →"
- After first outfit recommended: small tooltip on Save button "Save this for later →"
- Never show same tooltip twice

---

## Performance UX

### Perceived performance rules
- Show skeleton cards immediately — before data loads
- Show uploaded photo preview before AI analysis starts
- Show occasion tiles immediately — do not wait for wardrobe to load first
- Animate score bars after cards appear — not before

### Image optimisation
- Compress uploaded photos to max 800×800px before storing
- Show low-res thumbnail in grid, full image only on detail page
- Lazy load images below the fold

---

## Design Handoff Checklist

Before passing to development:

- [ ] All 7 pages have desktop + mobile designs
- [ ] All states designed: default, hover, active, disabled, loading, error, empty
- [ ] All components in a shared component library (Figma / Sketch)
- [ ] Color tokens defined and named
- [ ] Typography scale applied consistently
- [ ] All icons from a single icon library (e.g. Lucide, Heroicons)
- [ ] All tap targets verified at 44×44px minimum
- [ ] Contrast ratios verified for all text + background combinations
- [ ] Reduced motion variant considered
- [ ] All alt text written for images
- [ ] All transitions documented with duration + easing
- [ ] All micro-interactions prototyped or clearly described
- [ ] Spacing consistent with 8px grid
- [ ] Designs exported at 1x, 2x, 3x for all assets

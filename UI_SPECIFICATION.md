# AI Wardrobe Stylist — Full UI Specification
# For Frontend Team
# Every page, every component, every interaction

---

## App Structure (Pages)

```
/onboarding          → First time user setup
/wardrobe            → Main wardrobe grid (home page)
/wardrobe/upload     → Upload garment photo
/wardrobe/:id        → Single garment detail + edit
/recommend           → Occasion selector + outfit results
/collections         → Saved outfit collections
/collection/:id      → Single collection detail
```

---

## PAGE 1 — Onboarding  `/onboarding`

**When it shows:** Only when the user has 0 garments in their wardrobe (first visit).

### Layout
```
┌─────────────────────────────────────────────────────┐
│                                                     │
│           [App Logo + Name]                         │
│                                                     │
│        AI Wardrobe Stylist                          │
│        "Upload your clothes. Get outfit ideas."     │
│                                                     │
│    ┌─────────────────────────────────────────┐     │
│    │                                         │     │
│    │   📷  Upload your first garment         │     │
│    │       to get started                    │     │
│    │                                         │     │
│    │        [Upload Photo Button]            │     │
│    │                                         │     │
│    └─────────────────────────────────────────┘     │
│                                                     │
│    Or  [Skip — I'll add clothes later]              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Elements
- App logo (top center)
- App name: "AI Wardrobe Stylist"
- One-line description
- Large upload CTA button — primary color
- Skip link — takes user to empty wardrobe page
- No navigation bar on this page

### Behavior
- Upload Photo button → goes directly to `/wardrobe/upload`
- Skip → goes to `/wardrobe` with empty state
- If user already has garments → redirect to `/wardrobe`

---

## PAGE 2 — Wardrobe Grid  `/wardrobe`

**This is the home page of the app.**

### Layout
```
┌─────────────────────────────────────────────────────┐
│  [Logo]     Wardrobe (12)        [+ Add Garment]    │  ← Top nav bar
├─────────────────────────────────────────────────────┤
│  Filter by:  [Category ▼]  [Color ▼]  [Occasion ▼] │  ← Filter bar
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   │
│  │[Image] │  │[Image] │  │[Image] │  │[Image] │   │
│  │Navy    │  │White   │  │Black   │  │Brown   │   │
│  │Blazer  │  │Tee     │  │Jeans   │  │Loafers │   │
│  │outerwear│ │top     │  │bottom  │  │footwear│   │
│  └────────┘  └────────┘  └────────┘  └────────┘   │
│                                                     │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   │
│  │[Image] │  │[Image] │  │[Image] │  │  + Add │   │
│  │...     │  │...     │  │...     │  │        │   │
│  └────────┘  └────────┘  └────────┘  └────────┘   │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [Wardrobe] [Recommend] [Collections]               │  ← Bottom nav
└─────────────────────────────────────────────────────┘
```

### Top Navigation Bar
- Left: App logo (small)
- Center: "Wardrobe (N)" — N = total garment count, updates live
- Right: "+ Add Garment" button → goes to `/wardrobe/upload`

### Filter Bar
- **Category dropdown:** All / Tops / Bottoms / Outerwear / Footwear / Full Outfits
- **Color dropdown:** All / Black / White / Navy / Gray / Beige / (all colors from rules.json)
- **Occasion dropdown:** All / Casual / Formal / Business Casual / Outdoor / Sport
- Filters are combinable — applying multiple filters narrows results
- Active filter has a visible highlight/badge
- "Clear filters" link appears when any filter is active

### Garment Card (each item in the grid)
```
┌──────────────────┐
│                  │
│   [Photo or      │
│    Color Block   │
│    if no photo]  │
│                  │
│  Navy Blazer     │  ← garment name (truncated at 20 chars)
│  Outerwear       │  ← category
│  ● Navy          │  ← color dot + color name
└──────────────────┘
```
- Tapping a card → goes to `/wardrobe/:id`
- Long press (mobile) / right click (desktop) → shows quick actions: Edit, Delete
- If no photo uploaded → show a colored rectangle using the garment's primary color

### Empty State (0 garments)
```
┌─────────────────────────────────────────────────────┐
│                                                     │
│              👔                                     │
│                                                     │
│       Your wardrobe is empty                        │
│       Upload your first garment to get started      │
│                                                     │
│            [Upload a Garment]                       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Bottom Navigation Bar
Three tabs — always visible:
1. **Wardrobe** (active on this page) — wardrobe icon
2. **Recommend** — sparkle/wand icon
3. **Collections** — bookmark icon

---

## PAGE 3 — Upload Garment  `/wardrobe/upload`

**Flow: Photo → CLIP extracts attributes → User reviews → Confirm → Saved**

### Step 1 — Photo Selection
```
┌─────────────────────────────────────────────────────┐
│  ← Back         Add Garment                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │                                             │   │
│  │          📷  Upload Photo                   │   │
│  │                                             │   │
│  │     Drag and drop or click to browse        │   │
│  │     JPEG / PNG only · Max 5 MB              │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│           — or —                                    │
│                                                     │
│         [Take Photo with Camera]                    │
│                                                     │
│         [Enter Details Manually]                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Validation:**
- File not JPEG or PNG → red error: "Only JPEG and PNG files are accepted"
- File > 5 MB → red error: "File too large. Maximum size is 5 MB"
- Both errors appear inline below the upload box, not as a popup

### Step 2 — AI Processing (Loading State)
```
┌─────────────────────────────────────────────────────┐
│  ← Back         Add Garment                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│         [Uploaded photo preview — large]            │
│                                                     │
│              ⏳ Analysing garment...                │
│                                                     │
│    [████████████░░░░░░░░░]  60%                    │
│                                                     │
│    Identifying garment type...                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```
- Progress bar animates during CLIP processing
- Must complete within 5 seconds (Requirement 1, criterion 2)
- Show the photo immediately above so user knows it uploaded

### Step 3 — Review Extracted Attributes
```
┌─────────────────────────────────────────────────────┐
│  ← Back         Review Details          [Save]     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Photo — left side, 40% width]                    │
│                                                     │
│  Garment Name *                                     │
│  ┌───────────────────────────────────┐             │
│  │  Navy Blazer                      │             │
│  └───────────────────────────────────┘             │
│                                                     │
│  Garment Type *          ⚠️ Verify                  │
│  ┌───────────────────────────────────┐             │
│  │  Blazer                        ▼ │             │
│  └───────────────────────────────────┘             │
│                                                     │
│  Primary Color *                                    │
│  ┌───────────────────────────────────┐             │
│  │  ● Navy                        ▼ │             │
│  └───────────────────────────────────┘             │
│                                                     │
│  Secondary Color                                    │
│  ┌───────────────────────────────────┐             │
│  │  Gray                          ▼ │             │
│  └───────────────────────────────────┘             │
│                                                     │
│  Fabric                                             │
│  ┌───────────────────────────────────┐             │
│  │  Wool                          ▼ │             │
│  └───────────────────────────────────┘             │
│                                                     │
│  Pattern                                            │
│  ┌───────────────────────────────────┐             │
│  │  Solid                         ▼ │             │
│  └───────────────────────────────────┘             │
│                                                     │
│  Fit                                                │
│  ┌───────────────────────────────────┐             │
│  │  Tailored Fit                  ▼ │             │
│  └───────────────────────────────────┘             │
│                                                     │
│  Occasion Tags (select all that apply)              │
│  [Casual] [Formal ✓] [Business Casual ✓]           │
│  [Outdoor] [Sport]                                  │
│                                                     │
│                   [Save Garment]                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**⚠️ Low Confidence Warning:**
- Any field where CLIP confidence < 60% shows a yellow ⚠️ badge
- Tooltip on hover: "AI was not confident about this. Please verify."
- Field is still pre-filled — user just needs to confirm or change it

**All fields are editable dropdowns** — user can change any value CLIP got wrong.

**Garment Name field:**
- Pre-filled with: `{Primary Color} {Garment Type}` — e.g. "Navy Blazer"
- User can edit freely
- Validation: 1–100 characters
- Error shown inline if empty or too long

**Save button:**
- Disabled until Garment Name is filled
- On click → saves to DB → confirmation toast → redirects to `/wardrobe`
- Must confirm within 2 seconds (Requirement 1, criterion 6)

**Manual Entry option:**
- If user chose "Enter Details Manually" in Step 1 → same form but all fields blank (no photo, no AI pre-fill)

---

## PAGE 4 — Garment Detail & Edit  `/wardrobe/:id`

### Layout
```
┌─────────────────────────────────────────────────────┐
│  ← Back         Navy Blazer          [Edit] [🗑️]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│         [Full garment photo — large]                │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Type        Blazer                                 │
│  Category    Outerwear                              │
│  Color       ● Navy  /  ● Gray (secondary)         │
│  Fabric      Wool                                   │
│  Pattern     Solid                                  │
│  Fit         Tailored Fit                           │
│  Style       Smart Casual                           │
│                                                     │
│  Occasions   [Formal] [Business Casual]             │
│                                                     │
│  Added       June 9, 2026                          │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Appears in outfits:                                │
│  ┌──────────┐  ┌──────────┐                        │
│  │Outfit 1  │  │Outfit 2  │                        │
│  │Score: 87 │  │Score: 79 │                        │
│  └──────────┘  └──────────┘                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Edit Mode
- Tapping [Edit] converts all attribute rows into editable dropdowns (same options as upload form)
- [Save Changes] button appears at bottom
- [Cancel] restores original values
- On save → updates DB → updates Vector Store embedding → shows success toast

### Delete
- Trash icon in top right
- Confirmation dialog: "Delete Navy Blazer? This cannot be undone."
- Buttons: [Cancel] [Delete]
- On confirm → removes garment + its embedding → returns to `/wardrobe`

---

## PAGE 5 — Outfit Recommendations  `/recommend`

**This is the core feature of the app.**

### Step 1 — Occasion Selector
```
┌─────────────────────────────────────────────────────┐
│  [Logo]        Recommendations                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│   What's the occasion?                              │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ 👔 Everyday  │  │ 💼 Office   │  │ 🎓 College│  │
│  └─────────────┘  └─────────────┘  └───────────┘  │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ 🎉 Party    │  │ 💑 Date     │  │ 💒 Wedding│  │
│  └─────────────┘  └─────────────┘  └───────────┘  │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ 🌿 Outdoor  │  │ 🏋️ Gym      │  │ ✈️ Travel │  │
│  └─────────────┘  └─────────────┘  └───────────┘  │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐                  │
│  │ 🍽️ Formal   │  │ 🎪 Festival │                  │
│  │   Dinner   │  │             │                  │
│  └─────────────┘  └─────────────┘                  │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [Wardrobe]  [Recommend ●]  [Collections]           │
└─────────────────────────────────────────────────────┘
```

- Tapping an occasion tile immediately triggers outfit generation (no separate button)
- Selected tile gets a highlight border
- Occasion tiles are icons + label
- If wardrobe is empty → show message: "Add some clothes first" with link to upload

### Step 2 — Loading State
```
┌─────────────────────────────────────────────────────┐
│  ← Back      Outfits for Office                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│           ✨ Finding your best outfits...           │
│                                                     │
│    [Animated loading spinner or shimmer cards]      │
│                                                     │
│    Scoring outfit combinations...                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Step 3 — Results (Top 3 Outfit Cards)
```
┌─────────────────────────────────────────────────────┐
│  ← Back      Outfits for Office       [♻️ Refresh] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  #1  Best Match                   87/100    │   │  ← Score badge
│  │                                             │   │
│  │  [Blazer]  [Trousers]  [Loafers]            │   │  ← Garment images row
│  │                                             │   │
│  │  Navy Blazer · Gray Trousers · Brown Loafers│   │  ← Names
│  │                                             │   │
│  │  ████████████████████████░░░░  87%          │   │  ← Score bar
│  │                                             │   │
│  │  "Navy and gray are reliable tonal          │   │  ← Explanation
│  │   companions. Tailored fit with slim        │   │     (LLM-generated,
│  │   trousers creates clean proportions        │   │      placeholder
│  │   for office wear."                         │   │      until Gemini
│  │                                             │   │      is integrated)
│  │  [♡ Save to Collection]                     │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  #2                               79/100    │   │
│  │  ⚠️ Low confidence (0.54)                   │   │  ← Yellow warning
│  │                                             │   │
│  │  [Shirt]  [Chinos]  [Loafers]               │   │
│  │                                             │   │
│  │  White Shirt · Khaki Chinos · Brown Loafers │   │
│  │                                             │   │
│  │  ████████████████████░░░░░░░  79%           │   │
│  │                                             │   │
│  │  "Classic smart casual formula.             │   │
│  │   White shirt grounds the outfit and        │   │
│  │   khaki chinos add relaxed elegance."       │   │
│  │                                             │   │
│  │  [♡ Save to Collection]                     │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  #3                               71/100    │   │
│  │  ...                                        │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [Wardrobe]  [Recommend ●]  [Collections]           │
└─────────────────────────────────────────────────────┘
```

### Outfit Card — Detailed Breakdown

Every card contains:

| Element | Details |
|---------|---------|
| Rank badge | #1 Best Match / #2 / #3 |
| Score badge | e.g. "87/100" — top right corner |
| Score bar | Colored progress bar — green ≥75, yellow 50-74, red <50 |
| Low confidence badge | Yellow ⚠️ banner — only shows when confidence < 0.6 |
| Garment images | Row of circular or square images, one per garment |
| Garment names | Listed below images, comma separated |
| Explanation text | 20–100 words (LLM-generated) |
| Save button | Heart icon + "Save to Collection" |

### Save to Collection — Modal
```
┌──────────────────────────────────────┐
│   Save Outfit                        │
│                                      │
│   Collection name:                   │
│   ┌──────────────────────────────┐   │
│   │  My Office Looks             │   │
│   └──────────────────────────────┘   │
│   1–50 characters                    │
│                                      │
│   [Cancel]        [Save]             │
└──────────────────────────────────────┘
```
- Validation: empty name or > 50 chars → inline error under input
- On save → toast: "Saved to My Office Looks ✓"
- Toast disappears after 3 seconds
- If save fails → red toast: "Save failed. Try again."

### No Results State
```
If no garments match the selected occasion:

"No outfits found for Office.
 Try adding more garments or selecting a different occasion."

[Add Garments]   [Try Another Occasion]
```

---

## PAGE 6 — Collections  `/collections`

### Layout
```
┌─────────────────────────────────────────────────────┐
│  [Logo]         Collections                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  My Office Looks             3 outfits  →           │
│  ─────────────────────────────────────────          │
│  Date Night                  1 outfit   →           │
│  ─────────────────────────────────────────          │
│  Casual Weekends             5 outfits  →           │
│  ─────────────────────────────────────────          │
│                                                     │
│  ─────────────────────────────────────────          │
│                                                     │
│              No more collections.                   │
│                                                     │
│         Go to Recommend to save outfits.            │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [Wardrobe]  [Recommend]  [Collections ●]           │
└─────────────────────────────────────────────────────┘
```

- Each collection row shows: name + outfit count + arrow
- Tapping → goes to `/collection/:id`
- Empty state: "No saved collections yet. Find outfits and save them."

---

## PAGE 7 — Collection Detail  `/collection/:id`

### Layout
```
┌─────────────────────────────────────────────────────┐
│  ← Back    My Office Looks (3)      [Rename] [🗑️]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Outfit 1                         87/100    │   │
│  │  [Images row]                               │   │
│  │  Navy Blazer · Gray Trousers · Brown Loafers│   │
│  │  Office · June 9                            │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Outfit 2                         79/100    │   │
│  │  ...                                        │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

- Rename → inline input replaces collection name (1–50 chars)
- Delete collection → confirmation dialog → removes entire collection
- Each outfit card in collection is read-only (no re-save needed)

---

## Global Components

### Toast Notifications
- Success: green background, white text, ✓ icon
- Error: red background, white text, ✗ icon
- Warning: yellow background, dark text, ⚠️ icon
- Duration: 3 seconds, then auto-dismiss
- Position: bottom center on mobile, top right on desktop

### Empty States
Every page with a list must have a designed empty state — not a blank screen.

### Error States
- API unavailable → "Something went wrong. Please try again." + Retry button
- Vision model unavailable → "AI analysis unavailable. Enter details manually."
- Scorer unavailable → "Scoring unavailable. Showing garments only."

### Loading States
- Skeleton/shimmer cards while data loads — not spinners
- Upload processing → animated progress bar with status text

---

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| Mobile | 320px – 767px | Single column, bottom nav |
| Tablet | 768px – 1023px | 2 columns, bottom nav |
| Desktop | 1024px – 1919px | 3-4 columns, side nav |
| Wide | 1920px | 4-5 columns, side nav |

---

## Color System (Suggested)

| Token | Color | Use |
|-------|-------|-----|
| Primary | #5a3fa0 (purple) | Buttons, active states, score bars |
| Primary light | #b39ddb | Hover states, secondary buttons |
| Background | #0f0f13 (dark) or #f8f8fc (light) | Page background |
| Surface | #1a1a2e (dark) or #ffffff (light) | Cards, modals |
| Border | #2a2a38 | Card borders, dividers |
| Success | #2a5a3a | Green toasts, high score |
| Warning | #7a6000 | Yellow badges, low confidence |
| Error | #7a2020 | Red toasts, errors |
| Text primary | #e2e2e8 | Main text |
| Text muted | #6060a0 | Labels, metadata |

---

## What NOT to Build (Out of Scope for Now)

- User authentication / login system (can mock a single user)
- LLM explanation (placeholder text is fine — "Style explanation coming soon")
- Vector Store / RAG pipeline (not needed for UI)
- Push notifications
- Social sharing

---

## Acceptance Checklist (from requirements.md)

Before handing back to ML team, verify:

- [ ] Garment name validates 1–100 characters
- [ ] Upload rejects files > 5 MB and non-JPEG/PNG
- [ ] Low confidence fields (< 0.6) show ⚠️ warning
- [ ] Max 3 outfit cards per recommendation result
- [ ] Low confidence outfit shows indicator with actual value
- [ ] Save collection name validates 1–50 characters
- [ ] Save confirmation appears within 2 seconds
- [ ] Entire UI works at 320px width (test on iPhone SE)
- [ ] Entire UI works at 1920px width
- [ ] Empty wardrobe state does not call the scoring model
- [ ] Error states exist for every API failure

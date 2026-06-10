# AI Wardrobe Stylist & Recommendation Engine

A web-based outfit recommendation system. The user photographs their garments — a pretrained vision model catalogs them — and the system scores outfit combinations from their wardrobe using an XGBoost model grounded in a structured fashion rule corpus. Top-ranked outfits are displayed as visual cards with explanations written by an LLM.

**This is not a chatbot.** The user interacts through structured inputs: photo uploads, occasion selectors, and outfit cards. The LLM only writes explanations for already-scored outfits.

---

## Table of Contents

1. [How It Works](#1-how-it-works)
2. [System Architecture](#2-system-architecture)
3. [Build Phases](#3-build-phases)
4. [Knowledge Base — File Reference](#4-knowledge-base--file-reference)
5. [JSON Schema Reference](#5-json-schema-reference)
6. [Style Categories](#6-style-categories)
7. [Outfit Scoring System](#7-outfit-scoring-system)
8. [Vector Store and Rule Retrieval](#8-vector-store-and-rule-retrieval)
9. [How to Add New Rules](#9-how-to-add-new-rules)
10. [Glossary](#10-glossary)

---

## 1. How It Works

```
1. User uploads garment photo
          ↓
2. Vision Model extracts attributes
   (color, fabric, category, pattern, fit)
          ↓
3. User reviews + confirms → saved to Wardrobe DB
          ↓
4. User selects an occasion
          ↓
5. Recommendation Engine generates outfit combinations
   from the user's wardrobe
          ↓
6. XGBoost Outfit Scorer scores each combination
   using Rule Corpus features
          ↓
7. Vector Store retrieves most relevant rules
   for context
          ↓
8. LLM writes a 20–100 word explanation
   for each scored outfit
          ↓
9. Top 3 Outfit Cards displayed to user
   (garment images + score + explanation)
```

The user makes two decisions: **what garments exist** (photo upload) and **what occasion** (selector). The system handles everything in between.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER                                  │
│   [Upload Photo]              [Select Occasion]              │
└────────┬──────────────────────────────┬──────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌──────────────────────────────┐
│  Vision Model   │          │     Recommendation Engine    │
│ (Gemini / CLIP) │          │                              │
│  EXTERNAL API   │          │  ┌────────────────────────┐  │
└────────┬────────┘          │  │  Vector Store          │  │
         │                   │  │  (rule + garment        │  │
         ▼                   │  │   embeddings)           │  │
┌─────────────────┐          │  └──────────┬─────────────┘  │
│  Wardrobe DB    │──────────►  ┌──────────▼─────────────┐  │
│  (garment       │          │  │  XGBoost Outfit Scorer  │  │
│   catalog)      │          │  │  (Rule Corpus features) │  │
└─────────────────┘          │  └──────────┬─────────────┘  │
                             │             │                  │
                             │  ┌──────────▼─────────────┐  │
                             │  │  LLM Stylist            │  │
                             │  │  (explanation only)     │  │
                             │  └──────────┬─────────────┘  │
                             └─────────────┼────────────────-┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │  Recommendation Display │
                              │  Top 3 Outfit Cards     │
                              │  Score + Images + Text  │
                              └────────────────────────┘
```

### Component Responsibilities

| Component | Role | Type |
|-----------|------|------|
| **Vision Model** | Extracts garment attributes from a photo | External API (Gemini Vision / CLIP) |
| **Wardrobe DB** | Stores the user's garment catalog | Built — persisted database |
| **Vector Store** | Stores embeddings of garments and rules for semantic retrieval | Built — vector database |
| **Rule Corpus** | JSON knowledge base of fashion rules powering XGBoost features | Built — JSON files in this repo |
| **XGBoost Outfit Scorer** | Scores outfit combinations 0–100 using Rule Corpus features | Built — trained ML model |
| **LLM Stylist** | Writes natural-language explanation for a scored outfit | External API (Gemini) — explanation only |
| **Recommendation Display** | Shows top 3 Outfit Cards with score, images, and explanation | Built — frontend UI |

---

## 3. Build Phases

### Phase 1 — Data Acquisition (Offline)
Clean and normalize raw fashion book text for knowledge extraction.
- Strip non-semantic Unicode characters (Cc, Cf categories)
- Normalize to NFC form; convert smart quotes and dashes to ASCII
- For PDFs: strip headers, footers, page numbers
- Output: cleaned `.txt` file + preprocessing report

### Phase 2 — Knowledge Extraction (Offline / Admin)
Feed cleaned text to an LLM to extract structured styling rules.
- LLM produces rules conforming to the Rule Corpus JSON schema
- Rule types: color pairing, fabric compatibility, occasion-appropriateness, layering/proportion
- Output: versioned Rule Corpus JSON with semantic version + ISO 8601 timestamp

### Phase 3 — Structured Representation
Compile extracted rules into the versioned JSON Rule Corpus used at inference time.
- Rules organized by style category (streetwear, Korean, techwear, luxury, classic menswear)
- Each file is independently versioned and safely appendable
- Output: all knowledge base JSON files in `/ai-wardrobe-stylist/`

### Phase 4 — Predictive Integration
Train XGBoost on Rule Corpus features and populate the Vector Store.
- Feature vectors derived from Rule Corpus lookup tables in `rules.json`
- All garments and rules embedded into Vector Store
- Output: trained `Outfit_Scorer` model + populated `Vector_Store`

---

## 4. Knowledge Base — File Reference

All knowledge files live in `/ai-wardrobe-stylist/`. Load `rulebook_index.json` first to discover all available files.

### File Map

```
ai-wardrobe-stylist/
│
├── rulebook_index.json          ← START HERE — index of all files
│
├── fashion_rulebook.json        ← Classic menswear (110 rules)
├── rules.json                   ← XGBoost feature lookup tables + scoring weights
│
├── rulebook_streetwear.json     ← Streetwear principles (15 rules + 10 formulas)
├── rulebook_korean.json         ← Korean fashion principles (11 rules + 10 formulas)
├── rulebook_techwear.json       ← Techwear principles (10 rules + layering guide + 5 formulas)
├── rulebook_luxury.json         ← Contemporary luxury principles (10 rules + 5 formulas)
│
├── outfit_formulas.json         ← 200 outfit formulas (50 per style category)
├── style_identification.json    ← Style classification rules + decision tree
├── master_rulebook.json         ← 400 actionable rules (100 per style category)
│
├── flowchart.html               ← Visual system flowchart
└── README.md                    ← This file
```

---

### `rulebook_index.json`
Master index. Contains every file's name, category, description, rule count, formula count, and sources. Load this first at system startup.

---

### `fashion_rulebook.json`
Core classic menswear knowledge from foundational style literature (Flusser, Sims, Marx).

| Section | Contents |
|---------|----------|
| `part1_color_rules` | Harmony principles, neutral combinations, accent color rules, clash pairs, seasonal palettes |
| `part2_fit_proportion_rules` | Shirt, jacket, and trouser fit rules; visual balance rules |
| `part3_garment_knowledge` | 11 garments — history, formality level, correct pairings, common mistakes |
| `part4_outfit_combination_rules` | 7 proven outfit combinations with occasion, footwear, and notes |
| `part5_style_systems` | 5 style families: Ivy, Prep, Americana, Military, Workwear |
| `part6_timeless_principles` | 12 fundamental dressing principles |
| `part7_master_rulebook` | 110 numbered rules |

---

### `rules.json`
Machine-readable lookup tables consumed directly by the XGBoost feature pipeline.

| Key | Used for |
|-----|---------|
| `color_rules.good_pairs` / `bad_pairs` | Color compatibility sub-score |
| `style_occasion_rules` | Style-to-occasion match sub-score |
| `footwear_style_rules` + `footwear_occasion_rules` | Footwear match sub-score |
| `pattern_rules` | Pattern compatibility sub-score |
| `fit_combination_rules` | Fit balance sub-score |
| `season_material_rules` | Season-material match sub-score |
| `scoring_weights` | Feature weights for XGBoost (sum to 1.0) |

---

### `rulebook_streetwear.json`
15 core streetwear principles + 10 outfit formulas.
Sources: *This Is Not a T-Shirt*, *The Incomplete*, *Out of the Box*.

Key principles: oversized/slim volume balance, sneaker-first outfit construction, graphic tee as the statement, logo hierarchy, color blocking rules, layering system, hype vs. timeless distinction.

---

### `rulebook_korean.json`
11 Korean fashion principles + 10 outfit formulas.
Sources: *K-Fashion*, *Seoul Fashion City*, Musinsa Editorial, Seoul Fashion Week.

Key principles: wide-leg trousers as default, cropped top proportion rule, tonal dressing (all warm or all cool), muted desaturated palette, maximum two visible layers, minimal accessories, no logos.

---

### `rulebook_techwear.json`
10 techwear principles + functional layering guide + 5 outfit formulas.
Sources: Acronym Archives, Veilance, Nike ACG, System Magazine.

Key principles: base/mid/shell layering system, utility-first design, GORE-TEX and technical fabric compatibility, all-black / black+olive / black+stone palette, articulated silhouette, modular clothing systems.

**Layering guide** (`layering_guide` key):
```
base_layer  → moisture management (merino, polyester mesh)
mid_layer   → thermal insulation (fleece, down, PrimaLoft)
shell_layer → weather protection (GORE-TEX, Pertex, nylon DWR)
```

---

### `rulebook_luxury.json`
10 contemporary luxury principles + 5 outfit formulas.
Sources: *The Italian Gentleman*, *Sprezzatura*, Tom Ford, Loro Piana, Brunello Cucinelli.

Key principles: quiet luxury (fabric not logos), texture hierarchy, neutral palette construction, sprezzatura (effortless appearance), unstructured relaxed tailoring, investment piece logic.

---

### `outfit_formulas.json`
200 outfit formulas — 50 per style category. Each formula has: `id`, `formula`, `occasion`, `season`, `why_it_works`.

| Category | ID range | Count |
|----------|----------|-------|
| Streetwear | SW-F001 – SW-F050 | 50 |
| Korean Fashion | KF-F001 – KF-F050 | 50 |
| Techwear | TW-F001 – TW-F050 | 50 |
| Contemporary Luxury | LX-F001 – LX-F050 | 50 |

Used by the Outfit_Scorer as training examples and by the LLM_Stylist as reference context.

---

### `style_identification.json`
Rules for classifying an outfit into a style category based on observable attributes.

- `style_signatures` — per-category fingerprints: silhouette, fabrics, footwear, layering, palette, accessories, distinguishing features
- `identification_decision_tree` — step-by-step yes/no branching: technical fabric? → logos? → wide-leg + muted? → luxury fabric?

Used by the Vision Model post-processing layer to tag a garment with a style category.

---

### `master_rulebook.json`
400 concise actionable rules — 100 per category — identified by a unique rule ID.

| Prefix | Category | Rules |
|--------|----------|-------|
| `SW` | Streetwear | SW001–SW100 |
| `KF` | Korean Fashion | KF001–KF100 |
| `TW` | Techwear | TW001–TW100 |
| `LX` | Contemporary Luxury | LX001–LX100 |

These rule IDs are cited in LLM_Stylist explanations and used as feature flags in the XGBoost pipeline.

---

## 5. JSON Schema Reference

### Core Principle Object (all category rulebooks)

```json
{
  "rule_name": "Short rule title",
  "description": "Full description of the rule",
  "why_it_works": "Visual or aesthetic logic",
  "when_to_use": "Contexts where the rule applies",
  "when_to_avoid": "Contexts where the rule should be skipped",
  "outfit_examples": ["Example outfit 1", "Example outfit 2"]
}
```

### Outfit Formula Object

```json
{
  "id": "XX-FNNN",
  "formula": "Garment A + Garment B + Garment C",
  "occasion": "Occasion 1, Occasion 2",
  "season": "Season 1, Season 2",
  "why_it_works": "Explanation of visual and stylistic logic"
}
```

### Category Rulebook File (top-level structure)

```json
{
  "version": "1.0.0",
  "category": "style_category_identifier",
  "sources": ["Source 1", "Source 2"],
  "core_principles": [ ...CorePrincipleObject ],
  "outfit_formulas": [ ...OutfitFormulaObject ]
}
```

### Scoring Weights (`rules.json`)

```json
{
  "scoring_weights": {
    "color_compatibility":   0.30,
    "style_occasion_match":  0.25,
    "footwear_match":        0.20,
    "pattern_compatibility": 0.10,
    "fit_combination":       0.10,
    "season_material_match": 0.05
  }
}
```

Weights sum to 1.0. Color compatibility has the highest weight (0.30) because it is the most visually dominant factor in outfit compatibility.

---

## 6. Style Categories

| Category | Source file | Formality range | Defining signals |
|----------|-------------|-----------------|-----------------|
| Classic Menswear | `fashion_rulebook.json` | Casual → Formal | Fit precision, heritage garments, neutral base, texture interest |
| Streetwear | `rulebook_streetwear.json` | Casual only | Oversized top + slim bottom, sneaker-first, logos, graphic tees |
| Korean Fashion | `rulebook_korean.json` | Casual → Smart Casual | Wide trousers as default, muted tones, tonal dressing, no logos |
| Techwear | `rulebook_techwear.json` | Casual / Functional | GORE-TEX, tactical palette, modular hardware, trail runners |
| Contemporary Luxury | `rulebook_luxury.json` | Casual → Semi-Formal | No logos, exceptional fabrics, neutral palette, sprezzatura |

---

## 7. Outfit Scoring System

The `Outfit_Scorer` (XGBoost) receives a feature vector per outfit and outputs:
- **Compatibility score** — integer 0–100
- **Confidence_Score** — float 0–1

### Feature Vector

| Feature | Source in `rules.json` | Weight |
|---------|------------------------|--------|
| Color compatibility | `color_rules.good_pairs` / `bad_pairs` | 0.30 |
| Style / occasion match | `style_occasion_rules` | 0.25 |
| Footwear match | `footwear_style_rules` + `footwear_occasion_rules` | 0.20 |
| Pattern compatibility | `pattern_rules` | 0.10 |
| Fit balance | `fit_combination_rules` | 0.10 |
| Season / fabric match | `season_material_rules` | 0.05 |

### Rules

- If any required feature cannot be computed → score = `-1`, Confidence_Score = `0`
- If Confidence_Score < 0.6 → show low-confidence indicator on Outfit Card
- Only top 3 scored outfits are passed to the Recommendation Display
- Rule Corpus version update → invalidate all cached scores
- Monotonicity guaranteed: more rules satisfied = equal or higher score

---

## 8. Vector Store and Rule Retrieval

The Vector Store enables the Outfit_Scorer and LLM_Stylist to operate on the most relevant fashion rules for a given outfit and occasion, rather than the entire Rule Corpus.

### What is stored

- One embedding per Garment (updated within 10 seconds of any Wardrobe change)
- One embedding per Rule Corpus rule (re-embedded within 5 minutes of a Corpus version update)

### Retrieval

- Default top-K = 5, range 1–20
- Similarity threshold = 0.7
- Fallback: if fewer than 3 results above threshold → use top-3 by raw score + set `low_confidence: true`
- Zero results → proceed with base Rule Corpus only, log the event

### Embedding update SLA

| Trigger | Target | SLA |
|---------|--------|-----|
| Garment added / updated / deleted | That garment's embedding | ≤ 10 seconds |
| New Rule Corpus version activated | All rule embeddings | ≤ 5 minutes (≥ 90% success) |

---

## 9. How to Add New Rules

Each style category is a separate file — adding rules to one file cannot break another.

### Adding a core principle

Open the relevant category file (e.g., `rulebook_streetwear.json`) and append to `core_principles`:

```json
{
  "rule_name": "Your Rule Name",
  "description": "What the rule states.",
  "why_it_works": "The visual or aesthetic logic.",
  "when_to_use": "Context where it applies.",
  "when_to_avoid": "Context where it should be skipped.",
  "outfit_examples": ["Example outfit 1", "Example outfit 2"]
}
```

### Adding an outfit formula

Open `outfit_formulas.json` and append to the relevant category array. Increment the ID from the last existing one:

```json
{
  "id": "SW-F051",
  "formula": "Garment A + Garment B + Garment C",
  "occasion": "Occasion 1, Occasion 2",
  "season": "Spring, Autumn",
  "why_it_works": "Explanation of visual logic."
}
```

### Adding a master rule

Open `master_rulebook.json` and append to the relevant array:

```json
"SW101: New rule text here."
```

### After any addition

Update `rulebook_index.json`:
- Increment `rule_count` or `formula_count` for the affected file
- Update `total_rules` or `total_formulas` at the root
- Set `last_updated` to today's date

### Adding a new style category

1. Create `rulebook_[category].json` following the Core Principle schema
2. Add an entry to `rulebook_index.json`
3. Add 100 rules to `master_rulebook.json`
4. Add 50 formulas to `outfit_formulas.json`
5. Add a style signature to `style_identification.json`

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **Vision Model** | Pretrained external model (Gemini Vision / CLIP) that extracts garment attributes from a photo. Not trained by this system. |
| **Garment** | A single clothing item extracted from a photo and stored in the Wardrobe |
| **Wardrobe** | The user's catalogued collection of Garments |
| **Outfit** | A combination of two or more Garments assembled for a specific occasion |
| **Occasion** | A labeled context for outfit selection (casual, formal, business casual, outdoor, sport) |
| **Rule Corpus** | Versioned JSON knowledge base of fashion rules — feeds the Outfit_Scorer as feature data |
| **Knowledge Extractor** | Offline LLM pipeline that reads fashion book text and produces Rule Corpus rules. Runs as an admin operation, not at inference time. |
| **Outfit Scorer** | XGBoost model that scores outfit combinations 0–100 using Rule Corpus features |
| **Vector Store** | Vector database holding garment and rule embeddings for semantic retrieval |
| **RAG Pipeline** | Retrieves relevant rules and garment embeddings from the Vector Store to provide context to the LLM Stylist |
| **LLM Stylist** | External LLM (Gemini) that writes a natural-language explanation for a scored outfit. Does not generate outfit combinations. |
| **Outfit Card** | UI component showing garment images, compatibility score, confidence indicator, and LLM explanation |
| **Recommendation Display** | The page/panel showing the top 3 Outfit Cards |
| **Color Compatibility Score** | Sub-score (0–100) for color harmony within an outfit |
| **Fabric Compatibility Score** | Sub-score (0–100) for fabric pairing within an outfit |
| **Confidence Score** | Value (0–1) returned by the Outfit Scorer alongside each compatibility score |
| **Sprezzatura** | Italian concept — the appearance of effortless style; studied carelessness |
| **Tonal Dressing** | Wearing different shades of the same color family in a single outfit |
| **Quiet Luxury** | Luxury communicated through fabric quality and restraint rather than logos |
| **Rule Corpus Version** | Semantic version number assigned to each compiled Rule Corpus file |
| **Admin** | User role with permission to trigger Rule Corpus updates and model retraining |

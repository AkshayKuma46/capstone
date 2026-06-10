# AI Wardrobe Stylist — Team Handoff Document

**Date:** June 9, 2026  
**Prepared by:** Nandakishor  
**For:** Frontend & Backend Team Members

---

## What This Project Is

An outfit recommendation engine. The user uploads photos of their garments — the system automatically identifies what the garment is — and when the user picks an occasion, the system recommends the best outfit combinations from their wardrobe with a compatibility score.

**It is NOT a chatbot.** No conversation. Just:
- Photo upload → garment gets catalogued
- Occasion select → top 3 outfit recommendations appear

---

## What Is Already Built (Your Input)

The AI/ML brain is fully complete. Your job is to build the interface and database around it.

### Files you will receive

```
ai-wardrobe-stylist/
│
├── detectionV3.py          ← Vision model (CLIP) — extracts garment attributes from photo
├── training_pipeline.py    ← Trains the XGBoost scoring model
├── full_pipeline_runner.py ← Runs everything end-to-end
│
├── rules.json              ← All scoring rules (color, fabric, fit, occasion weights)
├── fashion_rulebook.json   ← 110 classic menswear rules
├── master_rulebook.json    ← 510 rules across all style categories
├── outfit_formulas.json    ← 200 outfit formulas
│
├── requirements.md         ← Full system requirements (9 requirements)
├── README.md               ← Full technical documentation
└── flowchart.html          ← System flowchart (open in browser)
```

---

## System Architecture

```
User uploads photo
       │
       ▼
CLIP Vision Model         ← ALREADY BUILT (detectionV3.py)
       │
       ▼
Garment Attributes        ← ALREADY BUILT
{ garment_type, color, fabric, pattern, fit, style, category }
       │
       ▼
Wardrobe Database         ← YOUR JOB (Team Member A)
       │
       ▼
User selects occasion
       │
       ▼
XGBoost Scoring Model     ← ALREADY BUILT (training_pipeline.py)
       │
       ▼
Compatibility Score 0-100
+ Confidence Score 0-1
       │
       ▼
Web UI — Outfit Cards     ← YOUR JOB (Team Member B)
```

---

## Team Member A — Database (SQLite or Firebase)

### What you need to build

A database that stores garments and outfits.

### Garment Table Schema

```sql
CREATE TABLE garments (
    id            TEXT PRIMARY KEY,        -- UUID
    user_id       TEXT NOT NULL,           -- which user owns this
    name          TEXT NOT NULL,           -- 1-100 chars
    garment_type  TEXT NOT NULL,           -- e.g. "bomber jacket"
    category      TEXT NOT NULL,           -- top / bottom / outerwear / footwear / full_outfit
    primary_color TEXT NOT NULL,           -- e.g. "black"
    secondary_color TEXT,                  -- e.g. "white"
    fabric        TEXT,                    -- e.g. "cotton"
    pattern       TEXT,                    -- e.g. "solid"
    fit           TEXT,                    -- e.g. "slim fit"
    style         TEXT,                    -- e.g. "casual"
    occasion_tags TEXT,                    -- comma-separated: "casual,everyday,college"
    image_path    TEXT,                    -- path to uploaded image file
    confidence_scores TEXT,               -- JSON string of per-field confidence values
    low_confidence_fields TEXT,           -- comma-separated fields below 0.6 confidence
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Outfit Table Schema

```sql
CREATE TABLE outfits (
    id                  TEXT PRIMARY KEY,   -- UUID
    user_id             TEXT NOT NULL,
    occasion            TEXT NOT NULL,
    garment_ids         TEXT NOT NULL,      -- JSON array of garment IDs
    compatibility_score INTEGER NOT NULL,   -- 0-100
    confidence_score    REAL NOT NULL,      -- 0.0-1.0
    feature_vector      TEXT,              -- JSON string of 7 features
    collection_name     TEXT,              -- if user saved it
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### What the Python pipeline outputs (your input)

When `full_pipeline_runner.py` runs, it saves this JSON to `wardrobe_db/outfit_{timestamp}.json`:

```json
{
  "occasion": "office",
  "compatibility_score": 87,
  "confidence_score": 0.74,
  "features": {
    "color": 95.0,
    "fabric": 90.0,
    "style_occ": 95.0,
    "footwear": 90.0,
    "pattern": 100.0,
    "fit": 95.0,
    "balance": 100.0
  },
  "garments": [
    {
      "image_path": "wardrobe_images/jacket.jpg",
      "garment_type": "blazer",
      "category": "outerwear",
      "primary_color": "navy",
      "secondary_color": "gray",
      "fabric": "wool",
      "pattern": "solid",
      "fit": "tailored fit",
      "style": "smart casual",
      "occasion": "office",
      "season": "autumn",
      "low_confidence_fields": []
    }
  ]
}
```

**Your job:** read this JSON and write it into the database.

### Key rules from requirements.md

- Garment name: 1–100 characters (validate before saving)
- Image: JPEG or PNG only, max 5 MB
- Occasion tags from fixed list: `casual, formal, business casual, outdoor, sport`
- When garment is updated → re-embed in Vector Store within 10 seconds
- When garment is deleted → remove from DB and Vector Store

### Recommended stack

- **SQLite** — simplest, no server needed, good for prototype
- **Firebase Firestore** — if you want real-time sync and multi-user from day 1
- **Python**: `sqlite3` (built-in) or `firebase-admin` SDK

---

## Team Member B — Web UI (Frontend)

### What you need to build

Two screens:

**Screen 1 — Wardrobe (Garment Catalog)**
- Grid of garment cards (image + name + category + color)
- Upload button → triggers photo upload → CLIP runs → shows extracted attributes → user confirms
- Filter by: category, color, fabric, occasion tag
- Edit / Delete per garment

**Screen 2 — Outfit Recommendations**
- Occasion selector dropdown: `casual / formal / business casual / outdoor / sport / college / date night / party / gym / travel`
- "Find Outfits" button
- Shows top 3 Outfit Cards

### Outfit Card component

Each card must show:
```
┌─────────────────────────────────────┐
│  [Garment Image 1]  [Image 2]  ...  │
│  Garment names listed               │
│                                     │
│  Compatibility: 87/100  ████████░░  │
│  Confidence: 0.74                   │
│                                     │
│  "This outfit works because navy    │
│   and gray are tonal companions..." │  ← LLM explanation (coming later)
│                                     │
│  [Save to Collection]               │
└─────────────────────────────────────┘
```

If confidence < 0.6 → show yellow warning badge on card.

### Key rules from requirements.md

- Show max **3 outfit cards** per recommendation
- Explanation: 20–100 words referencing at least one styling rule
- Responsive: works from 320px to 1920px width
- Save to collection: name 1–50 characters
- Save confirmation within 2 seconds
- If no garments in wardrobe → show empty state, don't call the model

### Recommended stack

- **React** or **Next.js** — component-based, easy card UI
- **Tailwind CSS** — fast styling
- **Axios** — API calls to the Python backend
- **FastAPI** (Python) — wrap the pipeline as a REST API

---

## API Endpoints You Need (Backend)

These are the endpoints the frontend will call. The Python pipeline logic already exists — you just need to wrap it in FastAPI.

```
POST   /garments/upload          Upload photo → run CLIP → return attributes
POST   /garments                 Save confirmed garment to DB
GET    /garments                 Get all garments for a user
PUT    /garments/{id}            Update garment attributes
DELETE /garments/{id}            Delete garment

POST   /outfits/recommend        { user_id, occasion } → run XGBoost → return top 3
POST   /outfits/save             Save outfit to named collection
GET    /outfits/collections      Get saved outfit collections
```

### Example response from `/outfits/recommend`

```json
{
  "outfits": [
    {
      "rank": 1,
      "compatibility_score": 87,
      "confidence_score": 0.74,
      "low_confidence": false,
      "garments": [
        { "id": "abc123", "name": "Navy Blazer", "image_url": "...", "category": "outerwear" },
        { "id": "def456", "name": "Gray Trousers", "image_url": "...", "category": "bottom" },
        { "id": "ghi789", "name": "Brown Loafers", "image_url": "...", "category": "footwear" }
      ],
      "explanation": null
    }
  ]
}
```

`explanation` is null for now — LLM integration comes later.

---

## How to Run the AI Pipeline Locally (for testing)

```bash
# 1. Install dependencies
pip install xgboost scikit-learn transformers torch pillow fastapi uvicorn

# 2. Train the model (run once)
python training_pipeline.py

# 3. Test detection
python detectionV3.py

# 4. Full pipeline test
python full_pipeline_runner.py
```

---

## What NOT to Change

- Do not modify `rules.json` — this is the scoring engine's source of truth
- Do not modify `training_pipeline.py` scoring weights without consulting the ML team
- Do not change the garment object field names — the pipeline depends on exact keys:
  `garment_type, primary_color, secondary_color, fabric, pattern, fit, style, category`

---

## Questions?

Read `README.md` for full technical documentation.  
Read `requirements.md` for all acceptance criteria.  
Open `flowchart.html` in a browser for the visual system flow.

Contact Nandakishor for anything related to the AI/ML pipeline.

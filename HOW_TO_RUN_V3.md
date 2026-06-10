# How to Run detectionV3 in Google Colab

## Step 1 — Open Colab
Go to https://colab.research.google.com
Create a new notebook.

## Step 2 — Upload the script
In a Colab cell, run:
```python
from google.colab import files
files.upload()  # upload detectionV3.py
```

## Step 3 — Run the script
In the next cell:
```python
exec(open("detectionV3.py").read())
```

## Step 4 — Change the occasion
At the bottom of the script, change:
```python
results = run_full_pipeline(image_paths, occasion="everyday")
```
To any of: `everyday`, `office`, `party`, `wedding`, `college`, `date night`, `outdoor`, `gym`

---

## What V3 fixes over V2

| Problem in V2 | Fix in V3 |
|--------------|-----------|
| All labels mixed together → wrong winner | Each category runs separately → correct winner per field |
| No structured output | Clean garment object: { garment_type, color, fabric, pattern, fit, style, occasion, category } |
| No bridge to XGBoost | 7-feature vector computed and scored |
| No final score | Compatibility score 0-100 + Confidence score 0-1 |
| Color detection weak | Dedicated primary_color category run |
| No low-confidence warnings | Fields below 0.6 confidence are flagged |

---

## Output you will see

```
📷 Processing: my_jacket.jpg
   Garment type  : bomber jacket (78.3%)
   Primary color : black (82.1%)
   Fabric        : nylon (61.2%)
   Pattern       : solid (91.4%)
   Fit           : relaxed fit (55.0%)
   Style         : streetwear (70.3%)
   Category      : outerwear
   ⚠️  Low confidence — verify: ['fit']

──────────────────────────────────────────────────
🔢 Feature Vector:
   color_compatibility_score          90.0  █████████
   fabric_compatibility_score         80.0  ████████
   style_occasion_match_score         95.0  █████████
   footwear_match_score               65.0  ██████
   pattern_compatibility_score       100.0  ██████████
   fit_combination_score              60.0  ██████
   garment_category_balance          100.0  ██████████

═══════════════════════════════════════════════════
  COMPATIBILITY SCORE : 85 / 100
  CONFIDENCE SCORE    : 0.73 / 1.0

  VERDICT: ✅ Great outfit for this occasion
═══════════════════════════════════════════════════
```

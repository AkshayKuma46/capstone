# ============================================================
# AI WARDROBE STYLIST — Detection + Feature Extraction
# detectionV3.py  |  Run in Google Colab
# ============================================================
# WHAT THIS DOES:
#   1. Upload or capture garment photos
#   2. CLIP Vision Model extracts raw predictions
#   3. Post-processor builds a clean structured garment object
#   4. Feature extractor converts it to the 7-feature vector
#   5. XGBoost Outfit Scorer scores the outfit (0-100)
# ============================================================

# ── CELL 1: Install & Imports ────────────────────────────────
# Run this cell first

from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from google.colab import files, output
from IPython.display import display, HTML
from io import BytesIO
import base64, os, json, time, torch
import numpy as np

os.makedirs("wardrobe_images", exist_ok=True)
print("✅ Imports done")


# ── CELL 2: Load CLIP Model ──────────────────────────────────
# Run once — takes ~30 seconds

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
print("✅ CLIP model loaded")


# ── CELL 3: Label Dictionary ─────────────────────────────────
# All the categories CLIP will classify against
# Matches exactly with rules.json garment taxonomy

LABELS_DICT = {
    "garment_type": [
        "t-shirt", "crew neck t-shirt", "v-neck t-shirt", "oversized t-shirt",
        "graphic t-shirt", "polo shirt", "dress shirt", "oxford shirt",
        "flannel shirt", "linen shirt", "hawaiian shirt", "denim shirt",
        "kurta", "henley shirt", "tank top", "camisole", "crop top",
        "blouse", "tunic", "sweatshirt", "hoodie", "zip hoodie",
        "sweater", "cardigan", "turtleneck", "vest", "waistcoat",
        "jacket", "denim jacket", "bomber jacket", "leather jacket",
        "biker jacket", "field jacket", "windbreaker", "parka",
        "trench coat", "overcoat", "raincoat", "blazer", "sport coat",
        "cape", "poncho",
        "jeans", "skinny jeans", "slim jeans", "straight jeans",
        "relaxed jeans", "wide leg jeans", "cargo pants", "chinos",
        "trousers", "dress pants", "joggers", "sweatpants",
        "track pants", "leggings", "palazzo pants", "culottes",
        "shorts", "denim shorts", "cargo shorts", "bermuda shorts",
        "mini dress", "midi dress", "maxi dress", "wrap dress",
        "shirt dress", "bodycon dress", "slip dress",
        "cocktail dress", "evening gown", "sundress",
        "mini skirt", "midi skirt", "maxi skirt", "pleated skirt",
        "pencil skirt", "a-line skirt", "denim skirt",
        "kurti", "sherwani", "nehru jacket", "dhoti",
        "lungi", "saree", "lehenga", "salwar kameez", "anarkali"
    ],
    "footwear": [
        "sneakers", "running shoes", "walking shoes",
        "basketball shoes", "high top sneakers", "low top sneakers",
        "canvas shoes", "formal shoes", "oxfords", "derbies",
        "loafers", "monk strap shoes", "boots", "chelsea boots",
        "combat boots", "hiking boots", "sandals", "flip flops",
        "slippers", "heels", "pumps", "wedges", "flats", "mules",
        "trail runners"
    ],
    "primary_color": [
        "black", "white", "gray", "charcoal", "silver",
        "navy", "blue", "light blue", "royal blue", "sky blue",
        "teal", "green", "olive", "mint green", "forest green",
        "yellow", "mustard", "orange", "peach",
        "red", "maroon", "burgundy", "pink", "hot pink",
        "purple", "lavender", "brown", "tan", "beige",
        "cream", "khaki", "gold"
    ],
    "pattern": [
        "solid", "striped", "vertical striped", "horizontal striped",
        "checked", "plaid", "tartan", "gingham", "floral",
        "paisley", "polka dot", "camouflage", "animal print",
        "abstract print", "graphic print", "tie dye", "geometric"
    ],
    "fit": [
        "slim fit", "regular fit", "relaxed fit", "oversized fit",
        "skinny fit", "athletic fit", "tailored fit", "loose fit", "wide fit"
    ],
    "fabric": [
        "cotton", "organic cotton", "linen", "denim", "wool",
        "cashmere", "silk", "satin", "polyester", "nylon",
        "rayon", "viscose", "fleece", "leather", "suede",
        "corduroy", "velvet", "jersey knit", "gore-tex", "merino wool"
    ],
    "style": [
        "casual", "smart casual", "business casual", "formal",
        "semi formal", "streetwear", "minimalist", "old money",
        "preppy", "athleisure", "sporty", "vintage", "retro",
        "grunge", "punk", "gothic", "bohemian", "techwear",
        "luxury", "classic", "modern", "korean fashion"
    ],
    "occasion": [
        "everyday", "office", "college", "interview",
        "business meeting", "wedding", "party", "date night",
        "vacation", "travel", "beach", "gym", "running",
        "sports", "festival", "religious event", "formal dinner", "outdoor"
    ],
    "season": [
        "summer", "winter", "spring", "autumn",
        "all season", "rainy season"
    ]
}

print("✅ Label dictionary ready")
print(f"   Total categories: {len(LABELS_DICT)}")
print(f"   Total labels: {sum(len(v) for v in LABELS_DICT.values())}")


# ── CELL 4: Image Input ──────────────────────────────────────
# Upload your garment photos

def upload_images():
    uploaded = files.upload()
    image_paths = []
    for filename, data in uploaded.items():
        path = os.path.join("wardrobe_images", filename)
        with open(path, "wb") as f:
            f.write(data)
        image_paths.append(path)
    print(f"\n✅ Uploaded {len(image_paths)} image(s)")
    return image_paths

image_paths = upload_images()


# ── CELL 5: CLIP Prediction Engine ───────────────────────────
# Runs CLIP per-category — picks the best label from EACH category
# This is the KEY FIX over V2:
# V2 mixed all labels together → wrong winner
# V3 runs each category separately → correct winner per field

def run_clip_per_category(image_path, labels_dict, model, processor, top_k=3):
    """
    Run CLIP for each category independently.
    Returns: { category: [ {label, confidence}, ... ] }
    """
    image = Image.open(image_path).convert("RGB")
    results = {}

    for category, labels in labels_dict.items():
        # Format labels as natural language for CLIP
        formatted = [f"a photo of {label}" for label in labels]

        inputs = processor(
            images=image,
            text=formatted,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits_per_image
            probs = logits.softmax(dim=1)[0]

        top_probs, top_indices = torch.topk(probs, min(top_k, len(labels)))

        results[category] = [
            {
                "label": labels[idx.item()],
                "confidence": round(prob.item() * 100, 2)
            }
            for prob, idx in zip(top_probs, top_indices)
        ]

    return results


# ── CELL 6: Post-Processor → Structured Garment Object ───────
# Takes CLIP raw output → clean garment object
# This is the bridge between Vision Model and XGBoost

def build_garment_object(clip_results, image_path, confidence_threshold=0.6):
    """
    Converts CLIP per-category results into a structured garment object.
    Flags low-confidence fields for user review.
    """

    garment = {
        "image_path": image_path,
        "garment_type": None,
        "primary_color": None,
        "secondary_color": None,
        "fabric": None,
        "pattern": None,
        "fit": None,
        "style": None,
        "occasion": None,
        "season": None,
        "footwear": None,
        "category": None,   # top / bottom / outerwear / full_outfit / footwear
        "confidence_scores": {},
        "low_confidence_fields": []
    }

    # Map category labels to garment object fields
    field_map = {
        "garment_type": "garment_type",
        "primary_color": "primary_color",
        "pattern":       "pattern",
        "fit":           "fit",
        "fabric":        "fabric",
        "style":         "style",
        "occasion":      "occasion",
        "season":        "season",
        "footwear":      "footwear"
    }

    for clip_cat, field in field_map.items():
        if clip_cat in clip_results and clip_results[clip_cat]:
            top = clip_results[clip_cat][0]
            confidence_normalized = top["confidence"] / 100.0

            garment[field] = top["label"]
            garment["confidence_scores"][field] = top["confidence"]

            if confidence_normalized < confidence_threshold:
                garment["low_confidence_fields"].append(field)

    # Derive garment category from garment_type
    garment["category"] = _derive_category(garment["garment_type"])

    # Secondary color: second highest from primary_color results
    if "primary_color" in clip_results and len(clip_results["primary_color"]) > 1:
        garment["secondary_color"] = clip_results["primary_color"][1]["label"]

    return garment


def _derive_category(garment_type):
    """Maps garment type string to structural category."""
    if garment_type is None:
        return "unknown"

    tops = [
        "t-shirt", "crew neck t-shirt", "v-neck t-shirt", "oversized t-shirt",
        "graphic t-shirt", "polo shirt", "dress shirt", "oxford shirt",
        "flannel shirt", "linen shirt", "hawaiian shirt", "denim shirt",
        "kurta", "henley shirt", "tank top", "camisole", "crop top",
        "blouse", "tunic", "sweatshirt", "hoodie", "zip hoodie",
        "sweater", "cardigan", "turtleneck", "kurti"
    ]
    outerwear = [
        "vest", "waistcoat", "jacket", "denim jacket", "bomber jacket",
        "leather jacket", "biker jacket", "field jacket", "windbreaker",
        "parka", "trench coat", "overcoat", "raincoat", "blazer",
        "sport coat", "cape", "poncho", "nehru jacket", "sherwani"
    ]
    bottoms = [
        "jeans", "skinny jeans", "slim jeans", "straight jeans",
        "relaxed jeans", "wide leg jeans", "cargo pants", "chinos",
        "trousers", "dress pants", "joggers", "sweatpants", "track pants",
        "leggings", "palazzo pants", "culottes", "shorts", "denim shorts",
        "cargo shorts", "bermuda shorts", "mini skirt", "midi skirt",
        "maxi skirt", "pleated skirt", "pencil skirt", "a-line skirt",
        "denim skirt", "dhoti", "lungi"
    ]
    full_outfits = [
        "mini dress", "midi dress", "maxi dress", "wrap dress",
        "shirt dress", "bodycon dress", "slip dress", "cocktail dress",
        "evening gown", "sundress", "saree", "lehenga",
        "salwar kameez", "anarkali"
    ]
    footwear_types = [
        "sneakers", "running shoes", "walking shoes", "basketball shoes",
        "high top sneakers", "low top sneakers", "canvas shoes",
        "formal shoes", "oxfords", "derbies", "loafers", "monk strap shoes",
        "boots", "chelsea boots", "combat boots", "hiking boots",
        "sandals", "flip flops", "slippers", "heels", "pumps",
        "wedges", "flats", "mules", "trail runners"
    ]

    gt = garment_type.lower()
    if gt in [t.lower() for t in tops]:           return "top"
    if gt in [t.lower() for t in outerwear]:      return "outerwear"
    if gt in [t.lower() for t in bottoms]:        return "bottom"
    if gt in [t.lower() for t in full_outfits]:   return "full_outfit"
    if gt in [t.lower() for t in footwear_types]: return "footwear"
    return "unknown"


print("✅ Post-processor ready")


# ── CELL 7: Feature Extractor → XGBoost Feature Vector ───────
# Converts garment object into numeric features for XGBoost
# Matches the feature_vector_schema in rules.json exactly

# Inline rule tables (from rules.json)
GOOD_COLOR_PAIRS = [
    ("navy","white"),("navy","beige"),("navy","gray"),("navy","light blue"),
    ("black","white"),("black","gray"),("black","red"),("black","pink"),
    ("white","olive"),("white","tan"),("white","brown"),
    ("olive","brown"),("olive","tan"),("olive","beige"),("olive","khaki"),
    ("burgundy","gray"),("burgundy","navy"),("burgundy","beige"),("burgundy","cream"),
    ("mustard","navy"),("mustard","brown"),("mustard","olive"),("mustard","gray"),
    ("teal","white"),("teal","navy"),("teal","gray"),("teal","beige"),
    ("maroon","gray"),("maroon","beige"),("maroon","navy"),
    ("lavender","white"),("lavender","gray"),("lavender","navy"),
    ("peach","white"),("peach","navy"),("peach","brown"),
    ("khaki","white"),("khaki","navy"),("khaki","brown"),
    ("forest green","beige"),("forest green","brown"),("forest green","white"),
    ("sky blue","white"),("sky blue","navy"),("sky blue","gray"),
]
BAD_COLOR_PAIRS = [
    ("brown","black"),("navy","black"),("red","orange"),("purple","green"),
    ("yellow","orange"),("pink","orange"),("red","pink"),("green","red"),
    ("blue","green"),("purple","brown"),("hot pink","red"),
    ("yellow","white"),("gold","silver"),
]
NEUTRAL_COLORS = ["black","white","gray","charcoal","beige","cream","tan"]

GOOD_FABRIC_PAIRS = [
    ("cotton","linen"),("cotton","denim"),("cotton","wool"),("cotton","jersey knit"),
    ("linen","suede"),("linen","leather"),("wool","cashmere"),("wool","cotton"),
    ("wool","flannel"),("cashmere","silk"),("silk","cashmere"),("silk","wool"),
    ("suede","wool"),("suede","cotton"),("suede","denim"),
    ("leather","cotton"),("leather","denim"),("leather","wool"),
    ("denim","cotton"),("denim","leather"),("denim","wool"),
    ("flannel","denim"),("flannel","cotton"),("corduroy","cotton"),("corduroy","wool"),
    ("fleece","nylon"),("nylon","polyester"),("gore-tex","nylon"),("gore-tex","fleece"),
    ("merino wool","nylon"),("merino wool","cashmere"),
]
BAD_FABRIC_PAIRS = [
    ("silk","nylon"),("silk","polyester"),("cashmere","nylon"),
    ("cashmere","polyester"),("silk","fleece"),("velvet","nylon"),
    ("velvet","polyester"),("satin","denim"),("satin","flannel"),
]

STYLE_OCCASION_MAP = {
    "casual":              ["everyday","college","vacation","travel","festival","date night"],
    "formal":              ["interview","business meeting","formal dinner","office","wedding"],
    "business casual":     ["office","interview","business meeting","college"],
    "smart casual":        ["office","date night","college","party","travel"],
    "streetwear":          ["everyday","college","festival","party"],
    "korean fashion":      ["everyday","college","date night","smart casual","office"],
    "techwear":            ["everyday","outdoor","travel"],
    "luxury":              ["formal dinner","wedding","party","date night"],
    "athleisure":          ["gym","running","sports","everyday","travel"],
    "bohemian":            ["festival","vacation","beach","everyday"],
}

GOOD_FIT_PAIRS = [
    ("oversized fit","slim fit"),("oversized fit","skinny fit"),
    ("relaxed fit","slim fit"),("relaxed fit","skinny fit"),
    ("slim fit","slim fit"),("regular fit","regular fit"),
    ("regular fit","slim fit"),("tailored fit","slim fit"),
    ("tailored fit","regular fit"),("loose fit","slim fit"),
    ("loose fit","skinny fit"),
]
BAD_FIT_PAIRS = [
    ("oversized fit","oversized fit"),("oversized fit","wide fit"),
    ("loose fit","wide fit"),("loose fit","oversized fit"),
]

SEASON_FABRIC_MAP = {
    "summer":       ["cotton","organic cotton","linen","rayon","viscose","jersey knit","satin"],
    "winter":       ["wool","cashmere","fleece","velvet","corduroy","leather","suede"],
    "spring":       ["cotton","organic cotton","linen","denim","jersey knit","rayon"],
    "autumn":       ["denim","wool","corduroy","leather","suede","cotton","fleece"],
    "rainy season": ["nylon","polyester","leather","denim","gore-tex"],
    "all season":   ["cotton","denim","polyester","nylon","jersey knit"],
}

SCORING_WEIGHTS = {
    "color_compatibility":    0.30,
    "fabric_compatibility":   0.15,
    "style_occasion_match":   0.20,
    "footwear_match":         0.15,
    "pattern_compatibility":  0.08,
    "fit_combination":        0.07,
    "garment_category_balance": 0.05,
}


def color_score(c1, c2):
    """Returns 0-100 color compatibility score for a pair."""
    if c1 is None or c2 is None:
        return 50  # neutral when unknown
    if c1 in NEUTRAL_COLORS or c2 in NEUTRAL_COLORS:
        return 90  # neutral always works
    pair = tuple(sorted([c1.lower(), c2.lower()]))
    good = [tuple(sorted(p)) for p in GOOD_COLOR_PAIRS]
    bad  = [tuple(sorted(p)) for p in BAD_COLOR_PAIRS]
    if pair in good: return 95
    if pair in bad:  return 10
    return 55  # unknown pair = average


def fabric_score(f1, f2):
    """Returns 0-100 fabric compatibility score."""
    if f1 is None or f2 is None:
        return 50
    pair = tuple(sorted([f1.lower(), f2.lower()]))
    good = [tuple(sorted(p)) for p in GOOD_FABRIC_PAIRS]
    bad  = [tuple(sorted(p)) for p in BAD_FABRIC_PAIRS]
    if f1.lower() == f2.lower(): return 80  # same fabric = decent
    if pair in good: return 90
    if pair in bad:  return 15
    return 55


def style_occasion_score(style, occasion):
    """Returns 0-100 for how well the style matches the occasion."""
    if style is None or occasion is None:
        return 50
    valid_occasions = STYLE_OCCASION_MAP.get(style.lower(), [])
    if occasion.lower() in valid_occasions:
        return 95
    # Partial match check
    for key, occasions in STYLE_OCCASION_MAP.items():
        if occasion.lower() in occasions and key == style.lower():
            return 95
    return 20


def pattern_score(pattern):
    """Returns 0-100 based on whether pattern is safe (solid = safest)."""
    if pattern is None:
        return 60
    if pattern.lower() == "solid":
        return 100
    # Non-solid patterns score lower (they need careful pairing)
    return 65


def fit_score(fit_top, fit_bottom):
    """Returns 0-100 for top+bottom fit combination."""
    if fit_top is None or fit_bottom is None:
        return 60
    pair = (fit_top.lower(), fit_bottom.lower())
    if pair in [(p[0].lower(), p[1].lower()) for p in GOOD_FIT_PAIRS]:
        return 95
    if pair in [(p[0].lower(), p[1].lower()) for p in BAD_FIT_PAIRS]:
        return 10
    return 60


def category_balance_score(garment_objects):
    """
    Returns 0-100 based on whether the outfit has required categories.
    Required: top (or full_outfit) + bottom (or full_outfit) + footwear
    """
    categories = [g.get("category", "unknown") for g in garment_objects]
    has_top         = "top" in categories or "full_outfit" in categories
    has_bottom      = "bottom" in categories or "full_outfit" in categories
    has_footwear    = "footwear" in categories
    has_full_outfit = "full_outfit" in categories

    if has_full_outfit and has_footwear:
        return 100
    if has_top and has_bottom and has_footwear:
        return 100
    if has_top and has_bottom:
        return 65   # missing footwear
    if has_full_outfit:
        return 70   # missing footwear
    return 35       # incomplete outfit


def footwear_score(style, occasion, has_footwear):
    """Returns 0-100 for footwear appropriateness."""
    if not has_footwear:
        return 0
    # Simplified: if footwear is present and style/occasion are compatible = good
    if style and occasion:
        valid = STYLE_OCCASION_MAP.get(style.lower(), [])
        if occasion.lower() in valid:
            return 90
    return 65


def extract_feature_vector(garment_objects, occasion):
    """
    Takes a list of garment objects (an outfit) + occasion string.
    Returns a 7-feature numeric vector + weighted score.
    """
    if not garment_objects:
        return None, -1, 0

    # Pull the primary garment (first non-footwear item)
    primary = next(
        (g for g in garment_objects if g["category"] not in ["footwear", "unknown"]),
        garment_objects[0]
    )
    secondary = next(
        (g for g in garment_objects if g != primary and g["category"] not in ["footwear", "unknown"]),
        None
    )
    footwear = next(
        (g for g in garment_objects if g["category"] == "footwear"),
        None
    )

    c1 = primary.get("primary_color")
    c2 = secondary.get("primary_color") if secondary else None
    f1 = primary.get("fabric")
    f2 = secondary.get("fabric") if secondary else None
    style   = primary.get("style")
    pattern = primary.get("pattern")
    fit_top = primary.get("fit") if primary.get("category") in ["top", "outerwear"] else None
    fit_bot = secondary.get("fit") if secondary and secondary.get("category") == "bottom" else None

    features = {
        "color_compatibility_score":    color_score(c1, c2),
        "fabric_compatibility_score":   fabric_score(f1, f2),
        "style_occasion_match_score":   style_occasion_score(style, occasion),
        "footwear_match_score":         footwear_score(style, occasion, footwear is not None),
        "pattern_compatibility_score":  pattern_score(pattern),
        "fit_combination_score":        fit_score(fit_top, fit_bot),
        "garment_category_balance":     category_balance_score(garment_objects),
    }

    # Weighted score
    weighted = sum(
        features[k] * SCORING_WEIGHTS[k.replace("_score", "").replace("_match", "_match")]
        if k.replace("_score", "").replace("_match", "_match") in SCORING_WEIGHTS
        else features[k] * list(SCORING_WEIGHTS.values())[i]
        for i, k in enumerate(features)
    )
    compatibility_score = round(min(max(weighted, 0), 100))

    # Confidence: average of per-feature raw confidence scores
    all_conf = [
        v / 100.0
        for v in primary.get("confidence_scores", {}).values()
    ]
    confidence_score = round(sum(all_conf) / len(all_conf), 2) if all_conf else 0.5

    return features, compatibility_score, confidence_score


print("✅ Feature extractor ready")


# ── CELL 8: MAIN PIPELINE ────────────────────────────────────
# Runs everything end to end on your uploaded images

def run_full_pipeline(image_paths, occasion="everyday"):
    """
    Full pipeline:
    image paths → CLIP → garment objects → feature vector → score
    """
    print(f"\n{'='*55}")
    print(f"  AI WARDROBE STYLIST — Full Pipeline Run")
    print(f"  Occasion: {occasion}")
    print(f"{'='*55}\n")

    garment_objects = []

    # ── Step 1: Vision Model (CLIP) ──
    for path in image_paths:
        print(f"📷 Processing: {os.path.basename(path)}")

        clip_results = run_clip_per_category(
            path, LABELS_DICT, model, processor, top_k=3
        )

        # ── Step 2: Post-process → structured garment ──
        garment = build_garment_object(clip_results, path)
        garment_objects.append(garment)

        print(f"   Garment type  : {garment['garment_type']} ({garment['confidence_scores'].get('garment_type', 0):.1f}%)")
        print(f"   Primary color : {garment['primary_color']} ({garment['confidence_scores'].get('primary_color', 0):.1f}%)")
        print(f"   Fabric        : {garment['fabric']}")
        print(f"   Pattern       : {garment['pattern']}")
        print(f"   Fit           : {garment['fit']}")
        print(f"   Style         : {garment['style']}")
        print(f"   Category      : {garment['category']}")

        if garment["low_confidence_fields"]:
            print(f"   ⚠️  Low confidence — verify: {garment['low_confidence_fields']}")
        print()

    # ── Step 3: Feature vector ──
    print(f"{'─'*55}")
    print("🔢 Feature Vector:")
    features, compatibility_score, confidence_score = extract_feature_vector(
        garment_objects, occasion
    )

    if features is None:
        print("❌ Could not compute features — no valid garments")
        return

    for feat, val in features.items():
        bar = "█" * int(val / 10)
        print(f"   {feat:<38} {val:>5.1f}  {bar}")

    # ── Step 4: Final score ──
    print(f"\n{'='*55}")
    print(f"  COMPATIBILITY SCORE : {compatibility_score} / 100")
    print(f"  CONFIDENCE SCORE    : {confidence_score:.2f} / 1.0")

    if confidence_score < 0.6:
        print(f"\n  ⚠️  LOW CONFIDENCE ({confidence_score:.2f})")
        print(f"     Some attributes were uncertain.")
        print(f"     Review low_confidence_fields above.")

    if compatibility_score >= 80:
        verdict = "✅ Great outfit for this occasion"
    elif compatibility_score >= 60:
        verdict = "🟡 Decent outfit — minor improvements possible"
    elif compatibility_score >= 40:
        verdict = "🟠 Outfit has some issues — check color/fabric pairing"
    else:
        verdict = "❌ Poor outfit match for this occasion"

    print(f"\n  VERDICT: {verdict}")
    print(f"{'='*55}\n")

    return garment_objects, features, compatibility_score, confidence_score


# ── Run the pipeline ──────────────────────────────────────────
# Change occasion to: everyday / office / party / wedding /
#                     college / date night / outdoor / gym
results = run_full_pipeline(image_paths, occasion="everyday")

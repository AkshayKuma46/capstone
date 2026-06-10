# ============================================================
# AI WARDROBE STYLIST — Hard Training Pipeline
# training_pipeline.py  |  Run in Google Colab
# ============================================================
# WHAT THIS DOES:
#   1. Generates 500+ synthetic labeled outfit examples
#   2. Computes all 7 features per example from rules.json
#   3. Trains XGBoost on the feature vectors
#   4. Evaluates the model (accuracy, MAE, confusion matrix)
#   5. Saves the trained model for use in detectionV3.py
# ============================================================

# ── CELL 1: Install dependencies ────────────────────────────
# !pip install xgboost scikit-learn matplotlib seaborn

import json, random, os, pickle
import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_absolute_error, classification_report,
    confusion_matrix, r2_score
)
from sklearn.preprocessing import LabelEncoder
from itertools import combinations

random.seed(42)
np.random.seed(42)
print("✅ Dependencies loaded")


# ── CELL 2: Rule Tables (from rules.json) ───────────────────

NEUTRAL_COLORS = ["black", "white", "gray", "charcoal", "beige", "cream", "tan"]

GOOD_COLOR_PAIRS = set([
    ("navy","white"),("navy","beige"),("navy","gray"),("navy","light blue"),
    ("black","white"),("black","gray"),("black","red"),("black","pink"),("black","gold"),
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
])

BAD_COLOR_PAIRS = set([
    ("brown","black"),("navy","black"),("red","orange"),("purple","green"),
    ("yellow","orange"),("pink","orange"),("red","pink"),("green","red"),
    ("blue","green"),("purple","brown"),("hot pink","red"),
    ("yellow","white"),("gold","silver"),
])

GOOD_FABRIC_PAIRS = set([
    ("cotton","linen"),("cotton","denim"),("cotton","wool"),("cotton","jersey knit"),
    ("linen","suede"),("linen","leather"),("wool","cashmere"),("wool","cotton"),
    ("wool","flannel"),("cashmere","silk"),("silk","cashmere"),("silk","wool"),
    ("suede","wool"),("suede","cotton"),("suede","denim"),
    ("leather","cotton"),("leather","denim"),("leather","wool"),
    ("denim","cotton"),("denim","leather"),("denim","wool"),
    ("flannel","denim"),("flannel","cotton"),("corduroy","cotton"),("corduroy","wool"),
    ("fleece","nylon"),("nylon","polyester"),("gore-tex","nylon"),("gore-tex","fleece"),
    ("merino wool","nylon"),("merino wool","cashmere"),
])

BAD_FABRIC_PAIRS = set([
    ("silk","nylon"),("silk","polyester"),("cashmere","nylon"),
    ("cashmere","polyester"),("silk","fleece"),("velvet","nylon"),
    ("velvet","polyester"),("satin","denim"),("satin","flannel"),
])

STYLE_OCCASION_MAP = {
    "casual":           ["everyday","college","vacation","travel","festival","date night"],
    "formal":           ["interview","business meeting","formal dinner","office","wedding"],
    "business casual":  ["office","interview","business meeting","college"],
    "smart casual":     ["office","date night","college","party","travel"],
    "streetwear":       ["everyday","college","festival","party"],
    "korean fashion":   ["everyday","college","date night","office"],
    "techwear":         ["everyday","outdoor","travel"],
    "luxury":           ["formal dinner","wedding","party","date night"],
    "athleisure":       ["gym","running","sports","everyday"],
    "bohemian":         ["festival","vacation","beach","everyday"],
}

GOOD_FIT_PAIRS = set([
    ("oversized fit","slim fit"),("oversized fit","skinny fit"),
    ("relaxed fit","slim fit"),("relaxed fit","skinny fit"),
    ("slim fit","slim fit"),("regular fit","regular fit"),
    ("regular fit","slim fit"),("tailored fit","slim fit"),
    ("tailored fit","regular fit"),("loose fit","slim fit"),
    ("loose fit","skinny fit"),
])
BAD_FIT_PAIRS = set([
    ("oversized fit","oversized fit"),("oversized fit","wide fit"),
    ("loose fit","wide fit"),("loose fit","oversized fit"),
])

SEASON_FABRIC_MAP = {
    "summer":       ["cotton","linen","rayon","viscose","jersey knit","satin"],
    "winter":       ["wool","cashmere","fleece","velvet","corduroy","leather","suede"],
    "spring":       ["cotton","linen","denim","jersey knit","rayon"],
    "autumn":       ["denim","wool","corduroy","leather","suede","cotton","fleece"],
    "rainy season": ["nylon","polyester","leather","denim","gore-tex"],
    "all season":   ["cotton","denim","polyester","nylon","jersey knit"],
}

SCORING_WEIGHTS = {
    "color":    0.30,
    "fabric":   0.15,
    "style_occ":0.20,
    "footwear": 0.15,
    "pattern":  0.08,
    "fit":      0.07,
    "balance":  0.05,
}

print("✅ Rule tables loaded")


# ── CELL 3: Feature Computation Functions ───────────────────

def color_score(c1, c2):
    if c1 is None or c2 is None: return 50
    if c1 == c2: return 75
    if c1 in NEUTRAL_COLORS or c2 in NEUTRAL_COLORS: return 88
    pair = tuple(sorted([c1.lower(), c2.lower()]))
    norm_good = set(tuple(sorted(p)) for p in GOOD_COLOR_PAIRS)
    norm_bad  = set(tuple(sorted(p)) for p in BAD_COLOR_PAIRS)
    if pair in norm_good: return 95
    if pair in norm_bad:  return 8
    return 52

def fabric_score(f1, f2):
    if f1 is None or f2 is None: return 50
    if f1.lower() == f2.lower(): return 78
    pair = tuple(sorted([f1.lower(), f2.lower()]))
    norm_good = set(tuple(sorted(p)) for p in GOOD_FABRIC_PAIRS)
    norm_bad  = set(tuple(sorted(p)) for p in BAD_FABRIC_PAIRS)
    if pair in norm_good: return 92
    if pair in norm_bad:  return 10
    return 53

def style_occ_score(style, occasion):
    if style is None or occasion is None: return 50
    valid = STYLE_OCCASION_MAP.get(style.lower(), [])
    return 95 if occasion.lower() in valid else 18

def pattern_score(pattern):
    if pattern is None: return 60
    if pattern.lower() == "solid": return 100
    if pattern.lower() in ["striped","checked","plaid","gingham"]: return 72
    return 58

def fit_score(fit_top, fit_bot):
    if fit_top is None or fit_bot is None: return 60
    pair = (fit_top.lower(), fit_bot.lower())
    norm_good = set((a.lower(), b.lower()) for a, b in GOOD_FIT_PAIRS)
    norm_bad  = set((a.lower(), b.lower()) for a, b in BAD_FIT_PAIRS)
    if pair in norm_good: return 95
    if pair in norm_bad:  return 8
    return 58

def season_fabric_score(season, fabric):
    if season is None or fabric is None: return 60
    valid = SEASON_FABRIC_MAP.get(season.lower(), [])
    return 92 if fabric.lower() in valid else 30

def category_balance_score(categories):
    cats = [c.lower() for c in categories]
    has_top      = "top" in cats or "full_outfit" in cats
    has_bottom   = "bottom" in cats or "full_outfit" in cats
    has_footwear = "footwear" in cats
    if has_top and has_bottom and has_footwear: return 100
    if has_top and has_bottom: return 65
    if "full_outfit" in cats and has_footwear: return 100
    if "full_outfit" in cats: return 68
    return 30

def footwear_score(style, occasion, has_footwear):
    if not has_footwear: return 0
    if style and occasion:
        valid = STYLE_OCCASION_MAP.get(style.lower(), [])
        return 90 if occasion.lower() in valid else 45
    return 60

def compute_weighted_score(feats):
    keys = ["color","fabric","style_occ","footwear","pattern","fit","balance"]
    raw = sum(feats[k] * SCORING_WEIGHTS[k] for k in keys)
    return round(min(max(raw, 0), 100), 2)

print("✅ Feature functions ready")


# ── CELL 4: Synthetic Training Data Generator ───────────────
# Generates 600 realistic outfit examples with ground-truth scores

COLORS = [
    "black","white","gray","navy","beige","cream","tan",
    "burgundy","olive","mustard","teal","maroon","lavender",
    "peach","khaki","forest green","sky blue","red","pink",
    "brown","gold","light blue","royal blue"
]
FABRICS = [
    "cotton","linen","denim","wool","cashmere","silk","satin",
    "polyester","nylon","fleece","leather","suede","corduroy",
    "jersey knit","flannel","rayon","gore-tex","merino wool","velvet"
]
PATTERNS = ["solid","solid","solid","striped","checked","plaid","graphic print",
            "floral","camouflage","tie dye","polka dot","geometric"]
FIT_TOPS  = ["slim fit","regular fit","relaxed fit","oversized fit",
             "tailored fit","loose fit","athletic fit"]
FIT_BOTS  = ["slim fit","skinny fit","regular fit","relaxed fit",
             "wide fit","loose fit","tailored fit"]
STYLES    = list(STYLE_OCCASION_MAP.keys())
OCCASIONS = ["everyday","office","college","party","date night",
             "wedding","formal dinner","gym","outdoor","festival","travel","beach"]
SEASONS   = ["summer","winter","spring","autumn","rainy season","all season"]
CATEGORIES_TOP  = ["top","outerwear"]
CATEGORIES_BOT  = ["bottom","full_outfit"]

# Pre-defined high-score combos (ground truth positive examples)
HIGH_SCORE_OUTFITS = [
    # (color1, color2, fabric1, fabric2, style, occasion, pattern, fit_top, fit_bot, has_footwear, season)
    ("navy","white","wool","cotton","formal","office","solid","tailored fit","slim fit",True,"autumn"),
    ("black","white","cotton","denim","casual","everyday","solid","regular fit","slim fit",True,"spring"),
    ("cream","beige","linen","cotton","casual","vacation","solid","relaxed fit","regular fit",True,"summer"),
    ("navy","gray","cashmere","flannel","smart casual","date night","solid","slim fit","slim fit",True,"winter"),
    ("black","black","nylon","nylon","techwear","outdoor","solid","relaxed fit","slim fit",True,"rainy season"),
    ("white","beige","linen","linen","korean fashion","everyday","solid","oversized fit","wide fit",True,"summer"),
    ("black","gray","gore-tex","nylon","techwear","travel","solid","relaxed fit","slim fit",True,"autumn"),
    ("navy","cream","cashmere","flannel","luxury","date night","solid","tailored fit","slim fit",True,"winter"),
    ("olive","tan","cotton","denim","casual","college","solid","oversized fit","slim fit",True,"autumn"),
    ("gray","white","wool","cotton","business casual","office","solid","slim fit","slim fit",True,"winter"),
    ("burgundy","gray","cashmere","flannel","smart casual","party","solid","slim fit","slim fit",True,"winter"),
    ("mustard","navy","cotton","denim","casual","everyday","solid","relaxed fit","slim fit",True,"autumn"),
    ("cream","tan","linen","cotton","casual","beach","solid","relaxed fit","regular fit",True,"summer"),
    ("sky blue","white","cotton","cotton","casual","college","solid","regular fit","regular fit",True,"spring"),
    ("black","white","cotton","denim","streetwear","festival","graphic print","oversized fit","slim fit",True,"summer"),
]

# Pre-defined low-score combos (ground truth negative examples)
LOW_SCORE_OUTFITS = [
    ("navy","black","silk","nylon","formal","gym","solid","tailored fit","wide fit",False,"winter"),
    ("red","orange","polyester","satin","casual","office","graphic print","loose fit","wide fit",False,"summer"),
    ("brown","black","velvet","nylon","formal","beach","solid","tailored fit","wide fit",True,"winter"),
    ("yellow","orange","cotton","fleece","casual","wedding","tie dye","oversized fit","wide fit",True,"summer"),
    ("purple","green","satin","denim","formal","gym","floral","loose fit","wide fit",False,"spring"),
    ("gold","silver","silk","polyester","luxury","gym","solid","tailored fit","wide fit",True,"summer"),
    ("hot pink","red","polyester","satin","casual","interview","graphic print","oversized fit","wide fit",False,"summer"),
    ("green","red","nylon","cashmere","techwear","wedding","camouflage","loose fit","wide fit",True,"summer"),
]

def generate_random_outfit():
    """Generate a random outfit with computed ground-truth score."""
    c1 = random.choice(COLORS)
    c2 = random.choice(COLORS)
    f1 = random.choice(FABRICS)
    f2 = random.choice(FABRICS)
    pattern  = random.choice(PATTERNS)
    fit_top  = random.choice(FIT_TOPS)
    fit_bot  = random.choice(FIT_BOTS)
    style    = random.choice(STYLES)
    occasion = random.choice(OCCASIONS)
    season   = random.choice(SEASONS)
    has_fw   = random.random() > 0.15   # 85% chance has footwear
    # Random category balance — usually complete outfits
    r = random.random()
    if r < 0.70:   cats = ["top","bottom","footwear"] if has_fw else ["top","bottom"]
    elif r < 0.85: cats = ["full_outfit","footwear"] if has_fw else ["full_outfit"]
    else:          cats = ["top","bottom"]

    feats = {
        "color":     color_score(c1, c2),
        "fabric":    fabric_score(f1, f2),
        "style_occ": style_occ_score(style, occasion),
        "footwear":  footwear_score(style, occasion, has_fw),
        "pattern":   pattern_score(pattern),
        "fit":       fit_score(fit_top, fit_bot),
        "balance":   category_balance_score(cats),
    }
    score = compute_weighted_score(feats)
    return feats, score, {
        "c1":c1,"c2":c2,"f1":f1,"f2":f2,"pattern":pattern,
        "fit_top":fit_top,"fit_bot":fit_bot,"style":style,
        "occasion":occasion,"season":season,"has_fw":has_fw,"cats":cats
    }

def outfit_from_tuple(t, score_override=None):
    c1,c2,f1,f2,style,occasion,pattern,fit_top,fit_bot,has_fw,season = t
    cats = ["top","bottom","footwear"] if has_fw else ["top","bottom"]
    feats = {
        "color":     color_score(c1, c2),
        "fabric":    fabric_score(f1, f2),
        "style_occ": style_occ_score(style, occasion),
        "footwear":  footwear_score(style, occasion, has_fw),
        "pattern":   pattern_score(pattern),
        "fit":       fit_score(fit_top, fit_bot),
        "balance":   category_balance_score(cats),
    }
    score = score_override if score_override else compute_weighted_score(feats)
    return feats, score

def generate_dataset(n_random=500):
    rows = []

    # Add curated high-score examples (boosted to 85-98)
    for t in HIGH_SCORE_OUTFITS:
        feats, base_score = outfit_from_tuple(t)
        score = min(98, base_score + random.uniform(5, 15))
        rows.append({**feats, "score": round(score, 1)})

    # Add curated low-score examples (capped at 25)
    for t in LOW_SCORE_OUTFITS:
        feats, base_score = outfit_from_tuple(t)
        score = max(5, min(25, base_score - random.uniform(5, 15)))
        rows.append({**feats, "score": round(score, 1)})

    # Add random examples
    for _ in range(n_random):
        feats, score, _ = generate_random_outfit()
        # Add slight noise to scores to simulate real-world variance
        noise = random.gauss(0, 3)
        score = round(min(100, max(0, score + noise)), 1)
        rows.append({**feats, "score": score})

    df = pd.DataFrame(rows)
    print(f"✅ Dataset generated: {len(df)} examples")
    print(f"   Score distribution:")
    print(f"   0-30  (bad)   : {len(df[df.score <= 30]):>4} examples")
    print(f"   31-60 (medium): {len(df[(df.score > 30) & (df.score <= 60)]):>4} examples")
    print(f"   61-80 (good)  : {len(df[(df.score > 60) & (df.score <= 80)]):>4} examples")
    print(f"   81-100 (great): {len(df[df.score > 80]):>4} examples")
    return df

df = generate_dataset(n_random=520)
print(f"\n   Mean score: {df.score.mean():.1f}")
print(f"   Std  score: {df.score.std():.1f}")


# ── CELL 5: Prepare Features & Labels ───────────────────────

FEATURE_COLS = ["color","fabric","style_occ","footwear","pattern","fit","balance"]

X = df[FEATURE_COLS].values.astype(np.float32)
y_reg = df["score"].values.astype(np.float32)

# Also create classification labels (3 classes)
def score_to_class(s):
    if s <= 40:  return 0   # bad
    if s <= 70:  return 1   # medium
    return 2                # good

y_cls = np.array([score_to_class(s) for s in y_reg])

X_train, X_test, y_reg_train, y_reg_test, y_cls_train, y_cls_test = train_test_split(
    X, y_reg, y_cls, test_size=0.2, random_state=42, stratify=y_cls
)

print(f"✅ Data split:")
print(f"   Train: {len(X_train)} examples")
print(f"   Test : {len(X_test)}  examples")
print(f"\n   Class distribution in test set:")
classes = ["bad (0-40)","medium (41-70)","good (71-100)"]
for i, c in enumerate(classes):
    print(f"   {c}: {(y_cls_test == i).sum()}")


# ── CELL 6: Train XGBoost Regressor ─────────────────────────
# Regressor predicts the exact compatibility score 0-100

print("\n🔧 Training XGBoost Regressor...")

xgb_reg = xgb.XGBRegressor(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_alpha=0.1,
    reg_lambda=1.0,
    objective="reg:squarederror",
    eval_metric="mae",
    early_stopping_rounds=30,
    random_state=42,
    verbosity=0
)

xgb_reg.fit(
    X_train, y_reg_train,
    eval_set=[(X_test, y_reg_test)],
    verbose=False
)

y_pred_reg = xgb_reg.predict(X_test)
mae  = mean_absolute_error(y_reg_test, y_pred_reg)
r2   = r2_score(y_reg_test, y_pred_reg)

print(f"✅ Regressor trained")
print(f"   MAE  : {mae:.2f} points  (lower = better)")
print(f"   R²   : {r2:.3f}          (closer to 1.0 = better)")


# ── CELL 7: Train XGBoost Classifier ────────────────────────
# Classifier predicts class: 0=bad, 1=medium, 2=good
# Used to derive the Confidence_Score

print("\n🔧 Training XGBoost Classifier...")

xgb_clf = xgb.XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_alpha=0.1,
    reg_lambda=1.0,
    objective="multi:softprob",
    num_class=3,
    eval_metric="mlogloss",
    early_stopping_rounds=30,
    random_state=42,
    verbosity=0
)

xgb_clf.fit(
    X_train, y_cls_train,
    eval_set=[(X_test, y_cls_test)],
    verbose=False
)

y_pred_cls  = xgb_clf.predict(X_test)
y_pred_prob = xgb_clf.predict_proba(X_test)

print(f"✅ Classifier trained")
print(f"\n   Classification Report:")
print(classification_report(
    y_cls_test, y_pred_cls,
    target_names=["bad","medium","good"]
))


# ── CELL 8: Feature Importance ──────────────────────────────

importances = xgb_reg.feature_importances_
feat_imp = sorted(
    zip(FEATURE_COLS, importances),
    key=lambda x: x[1], reverse=True
)

print("📊 Feature Importance (Regressor):")
for feat, imp in feat_imp:
    bar = "█" * int(imp * 50)
    print(f"   {feat:<15} {imp:.4f}  {bar}")


# ── CELL 9: Confusion Matrix Plot ───────────────────────────

PLOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
cm = confusion_matrix(y_cls_test, y_pred_cls)
plt.figure(figsize=(7, 5))
sns.heatmap(
    cm, annot=True, fmt="d", cmap="Purples",
    xticklabels=["bad","medium","good"],
    yticklabels=["bad","medium","good"],
    linewidths=0.5
)
plt.title("XGBoost Classifier — Confusion Matrix", fontsize=13, fontweight="bold")
plt.xlabel("Predicted"); plt.ylabel("Actual")
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, "confusion_matrix.png"), dpi=150)
plt.close()
print("✅ Confusion matrix saved to models/confusion_matrix.png")


# ── CELL 10: Score Distribution Plot ────────────────────────

plt.figure(figsize=(10, 4))
plt.subplot(1, 2, 1)
plt.hist(y_reg_test, bins=20, color="#5a3fa0", alpha=0.7, label="Actual")
plt.hist(y_pred_reg, bins=20, color="#b39ddb", alpha=0.7, label="Predicted")
plt.xlabel("Compatibility Score"); plt.ylabel("Count")
plt.title("Actual vs Predicted Score Distribution")
plt.legend()
plt.subplot(1, 2, 2)
plt.scatter(y_reg_test, y_pred_reg, alpha=0.4, color="#5a3fa0", s=20)
plt.plot([0,100],[0,100], "r--", linewidth=1)
plt.xlabel("Actual Score"); plt.ylabel("Predicted Score")
plt.title(f"Actual vs Predicted  |  R²={r2:.3f}")
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, "score_distribution.png"), dpi=150)
plt.close()
print("✅ Score distribution saved to models/score_distribution.png")


# ── CELL 11: Cross-Validation ────────────────────────────────

print("\n🔍 5-Fold Cross Validation (Regressor, MAE)...")
cv_model = xgb.XGBRegressor(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0
)
cv_scores = cross_val_score(
    cv_model, X, y_reg,
    cv=5, scoring="neg_mean_absolute_error"
)
cv_mae = -cv_scores
print(f"   Fold MAEs: {[round(m,2) for m in cv_mae]}")
print(f"   Mean MAE : {cv_mae.mean():.2f} ± {cv_mae.std():.2f}")


# ── CELL 12: Save Trained Models ────────────────────────────

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
os.makedirs(MODELS_DIR, exist_ok=True)
print(f"   Saving models to: {MODELS_DIR}")

with open(os.path.join(MODELS_DIR, "xgb_regressor.pkl"), "wb") as f:
    pickle.dump(xgb_reg, f)

with open(os.path.join(MODELS_DIR, "xgb_classifier.pkl"), "wb") as f:
    pickle.dump(xgb_clf, f)

# Save model metadata
metadata = {
    "version": "1.0.0",
    "trained_on": pd.Timestamp.now().isoformat(),
    "training_examples": len(df),
    "feature_columns": FEATURE_COLS,
    "scoring_weights": SCORING_WEIGHTS,
    "regressor": {
        "n_estimators": int(xgb_reg.best_iteration),
        "mae_test": round(float(mae), 3),
        "r2_test":  round(float(r2), 3),
    },
    "classifier": {
        "classes": ["bad (0-40)", "medium (41-70)", "good (71-100)"],
        "accuracy_test": round(float((y_pred_cls == y_cls_test).mean()), 3),
    },
    "cv_mae_mean": round(float(cv_mae.mean()), 3),
    "cv_mae_std":  round(float(cv_mae.std()), 3),
}
with open(os.path.join(MODELS_DIR, "model_metadata.json"), "w") as f:
    json.dump(metadata, f, indent=2)

print(f"\n✅ Models saved to: {MODELS_DIR}")
print(f"   xgb_regressor.pkl")
print(f"   xgb_classifier.pkl")
print(f"   model_metadata.json")


# ── CELL 13: Inference Function ─────────────────────────────
# This is what detectionV3.py calls after CLIP extracts garment attributes

def predict_outfit_score(garment_objects, occasion, regressor, classifier):
    """
    Takes list of garment dicts (from detectionV3 build_garment_object)
    + occasion string.
    Returns compatibility_score (0-100) and confidence_score (0-1).
    """
    if not garment_objects:
        return -1, 0.0

    primary = next(
        (g for g in garment_objects if g.get("category") not in ["footwear","unknown"]),
        garment_objects[0]
    )
    secondary = next(
        (g for g in garment_objects
         if g != primary and g.get("category") not in ["footwear","unknown"]),
        None
    )
    footwear = next(
        (g for g in garment_objects if g.get("category") == "footwear"),
        None
    )

    c1      = primary.get("primary_color")
    c2      = secondary.get("primary_color") if secondary else None
    f1      = primary.get("fabric")
    f2      = secondary.get("fabric") if secondary else None
    style   = primary.get("style")
    pattern = primary.get("pattern")
    fit_top = primary.get("fit") if primary.get("category") in ["top","outerwear"] else None
    fit_bot = secondary.get("fit") if secondary and secondary.get("category") == "bottom" else None
    cats    = [g.get("category","unknown") for g in garment_objects]
    has_fw  = footwear is not None

    features = {
        "color":     color_score(c1, c2),
        "fabric":    fabric_score(f1, f2),
        "style_occ": style_occ_score(style, occasion),
        "footwear":  footwear_score(style, occasion, has_fw),
        "pattern":   pattern_score(pattern),
        "fit":       fit_score(fit_top, fit_bot),
        "balance":   category_balance_score(cats),
    }

    X_input = np.array([[features[k] for k in FEATURE_COLS]], dtype=np.float32)

    # Regressor → score
    score = round(float(regressor.predict(X_input)[0]))
    score = max(0, min(100, score))

    # Classifier → confidence (max probability of predicted class)
    probs      = classifier.predict_proba(X_input)[0]
    confidence = round(float(max(probs)), 2)

    return score, confidence, features


# ── CELL 14: Test Inference ──────────────────────────────────
# Simulate what detectionV3 would send after CLIP runs

test_outfits = [
    {
        "name": "Navy blazer outfit (should score HIGH)",
        "garments": [
            {"category":"top",      "primary_color":"navy",  "fabric":"wool",
             "pattern":"solid","fit":"tailored fit","style":"smart casual"},
            {"category":"bottom",   "primary_color":"gray",  "fabric":"flannel",
             "pattern":"solid","fit":"slim fit","style":"smart casual"},
            {"category":"footwear", "primary_color":"brown", "fabric":"leather",
             "pattern":"solid","fit":"slim fit","style":"smart casual"},
        ],
        "occasion": "office"
    },
    {
        "name": "All-black techwear (should score HIGH)",
        "garments": [
            {"category":"outerwear","primary_color":"black","fabric":"gore-tex",
             "pattern":"solid","fit":"relaxed fit","style":"techwear"},
            {"category":"bottom",  "primary_color":"black","fabric":"nylon",
             "pattern":"solid","fit":"slim fit","style":"techwear"},
            {"category":"footwear","primary_color":"black","fabric":"nylon",
             "pattern":"solid","fit":"slim fit","style":"techwear"},
        ],
        "occasion": "outdoor"
    },
    {
        "name": "Mismatched clash outfit (should score LOW)",
        "garments": [
            {"category":"top",    "primary_color":"navy",  "fabric":"silk",
             "pattern":"graphic print","fit":"oversized fit","style":"formal"},
            {"category":"bottom", "primary_color":"black", "fabric":"nylon",
             "pattern":"camouflage","fit":"wide fit","style":"techwear"},
        ],
        "occasion": "wedding"
    },
    {
        "name": "Korean fashion tonal (should score HIGH)",
        "garments": [
            {"category":"top",    "primary_color":"cream","fabric":"linen",
             "pattern":"solid","fit":"oversized fit","style":"korean fashion"},
            {"category":"bottom", "primary_color":"beige","fabric":"cotton",
             "pattern":"solid","fit":"wide fit","style":"korean fashion"},
            {"category":"footwear","primary_color":"white","fabric":"leather",
             "pattern":"solid","fit":"slim fit","style":"korean fashion"},
        ],
        "occasion": "everyday"
    },
    {
        "name": "Streetwear graphic tee (should score MEDIUM-HIGH)",
        "garments": [
            {"category":"top",    "primary_color":"white","fabric":"cotton",
             "pattern":"graphic print","fit":"oversized fit","style":"streetwear"},
            {"category":"bottom", "primary_color":"black","fabric":"denim",
             "pattern":"solid","fit":"slim fit","style":"streetwear"},
            {"category":"footwear","primary_color":"white","fabric":"cotton",
             "pattern":"solid","fit":"slim fit","style":"streetwear"},
        ],
        "occasion": "college"
    },
]

print("\n" + "="*60)
print("  INFERENCE TEST — Trained XGBoost on Real Outfits")
print("="*60)

for test in test_outfits:
    score, conf, feats = predict_outfit_score(
        test["garments"], test["occasion"],
        xgb_reg, xgb_clf
    )
    verdict = (
        "✅ GREAT"  if score >= 75 else
        "🟡 DECENT" if score >= 55 else
        "🟠 POOR"   if score >= 35 else
        "❌ BAD"
    )
    low_conf_warn = "  ⚠️  LOW CONFIDENCE" if conf < 0.6 else ""

    print(f"\n  {test['name']}")
    print(f"  Occasion : {test['occasion']}")
    print(f"  Score    : {score}/100   Confidence: {conf:.2f}  {verdict}{low_conf_warn}")
    print(f"  Features : color={feats['color']:.0f} fabric={feats['fabric']:.0f} "
          f"style_occ={feats['style_occ']:.0f} fit={feats['fit']:.0f} "
          f"pattern={feats['pattern']:.0f} balance={feats['balance']:.0f}")

print("\n" + "="*60)
print(f"  Model MAE  : {mae:.2f}  |  R² : {r2:.3f}")
print(f"  CV MAE     : {cv_mae.mean():.2f} ± {cv_mae.std():.2f}")
print("="*60)
print("\n✅ Full pipeline test complete")
print("   Models saved to /models/ — upload to your project")

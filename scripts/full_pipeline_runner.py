# ============================================================
# AI WARDROBE STYLIST — Full End-to-End Pipeline Runner
# full_pipeline_runner.py  |  Run in Google Colab
# ============================================================
# RUNS IN ORDER:
#   Step 1 → training_pipeline.py  (trains XGBoost)
#   Step 2 → detectionV3.py        (CLIP extracts garment attributes)
#   Step 3 → Links both together   (CLIP output → XGBoost → score)
# ============================================================

# ── CELL 1: Run training pipeline first ─────────────────────
print("=" * 60)
print("  STEP 1: TRAINING XGBOOST")
print("=" * 60)
exec(open("training_pipeline.py").read())
# After this: xgb_reg, xgb_clf, predict_outfit_score() are all live


# ── CELL 2: Load CLIP model ──────────────────────────────────
print("\n" + "=" * 60)
print("  STEP 2: LOADING CLIP VISION MODEL")
print("=" * 60)

from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from google.colab import files
import torch, os, json

os.makedirs("wardrobe_images", exist_ok=True)

clip_model     = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
print("✅ CLIP model loaded")


# ── CELL 3: Label dictionary for CLIP ───────────────────────

LABELS_DICT = {
    "garment_type": [
        "t-shirt","crew neck t-shirt","v-neck t-shirt","oversized t-shirt",
        "graphic t-shirt","polo shirt","dress shirt","oxford shirt",
        "flannel shirt","linen shirt","hawaiian shirt","denim shirt",
        "kurta","henley shirt","tank top","camisole","crop top",
        "blouse","tunic","sweatshirt","hoodie","zip hoodie",
        "sweater","cardigan","turtleneck","vest","waistcoat",
        "jacket","denim jacket","bomber jacket","leather jacket",
        "biker jacket","field jacket","windbreaker","parka",
        "trench coat","overcoat","raincoat","blazer","sport coat",
        "cape","poncho",
        "jeans","skinny jeans","slim jeans","straight jeans",
        "relaxed jeans","wide leg jeans","cargo pants","chinos",
        "trousers","dress pants","joggers","sweatpants",
        "track pants","leggings","palazzo pants","culottes",
        "shorts","denim shorts","cargo shorts","bermuda shorts",
        "mini dress","midi dress","maxi dress","wrap dress",
        "shirt dress","bodycon dress","slip dress",
        "cocktail dress","evening gown","sundress",
        "mini skirt","midi skirt","maxi skirt","pleated skirt",
        "pencil skirt","a-line skirt","denim skirt",
        "kurti","sherwani","nehru jacket","dhoti",
        "lungi","saree","lehenga","salwar kameez","anarkali"
    ],
    "footwear": [
        "sneakers","running shoes","walking shoes","basketball shoes",
        "high top sneakers","low top sneakers","canvas shoes",
        "formal shoes","oxfords","derbies","loafers","monk strap shoes",
        "boots","chelsea boots","combat boots","hiking boots","sandals",
        "flip flops","slippers","heels","pumps","wedges","flats","mules","trail runners"
    ],
    "primary_color": [
        "black","white","gray","charcoal","silver","navy","blue","light blue",
        "royal blue","sky blue","teal","green","olive","mint green","forest green",
        "yellow","mustard","orange","peach","red","maroon","burgundy",
        "pink","hot pink","purple","lavender","brown","tan","beige","cream","khaki","gold"
    ],
    "pattern": [
        "solid","striped","vertical striped","horizontal striped",
        "checked","plaid","tartan","gingham","floral","paisley","polka dot",
        "camouflage","animal print","abstract print","graphic print","tie dye","geometric"
    ],
    "fit": [
        "slim fit","regular fit","relaxed fit","oversized fit",
        "skinny fit","athletic fit","tailored fit","loose fit","wide fit"
    ],
    "fabric": [
        "cotton","organic cotton","linen","denim","wool","cashmere","silk",
        "satin","polyester","nylon","rayon","viscose","fleece","leather",
        "suede","corduroy","velvet","jersey knit","gore-tex","merino wool"
    ],
    "style": [
        "casual","smart casual","business casual","formal","semi formal",
        "streetwear","minimalist","old money","preppy","athleisure",
        "sporty","vintage","grunge","gothic","bohemian","techwear",
        "luxury","classic","modern","korean fashion"
    ],
    "occasion": [
        "everyday","office","college","interview","business meeting",
        "wedding","party","date night","vacation","travel","beach",
        "gym","running","sports","festival","religious event","formal dinner","outdoor"
    ],
    "season": [
        "summer","winter","spring","autumn","all season","rainy season"
    ]
}


# ── CELL 4: CLIP per-category runner ────────────────────────

def run_clip_per_category(image_path, labels_dict, model, processor, top_k=3):
    image = Image.open(image_path).convert("RGB")
    results = {}
    for category, labels in labels_dict.items():
        formatted = [f"a photo of {label}" for label in labels]
        inputs = processor(
            images=image, text=formatted,
            return_tensors="pt", padding=True
        )
        with torch.no_grad():
            outputs = model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)[0]
        top_probs, top_idx = torch.topk(probs, min(top_k, len(labels)))
        results[category] = [
            {"label": labels[i.item()], "confidence": round(p.item()*100, 2)}
            for p, i in zip(top_probs, top_idx)
        ]
    return results


# ── CELL 5: Post-processor ───────────────────────────────────

def _derive_category(gt):
    if gt is None: return "unknown"
    tops = ["t-shirt","crew neck t-shirt","v-neck t-shirt","oversized t-shirt",
            "graphic t-shirt","polo shirt","dress shirt","oxford shirt",
            "flannel shirt","linen shirt","hawaiian shirt","denim shirt","kurta",
            "henley shirt","tank top","camisole","crop top","blouse","tunic",
            "sweatshirt","hoodie","zip hoodie","sweater","cardigan","turtleneck","kurti"]
    outerwear = ["vest","waistcoat","jacket","denim jacket","bomber jacket",
                 "leather jacket","biker jacket","field jacket","windbreaker",
                 "parka","trench coat","overcoat","raincoat","blazer","sport coat",
                 "cape","poncho","nehru jacket","sherwani"]
    bottoms = ["jeans","skinny jeans","slim jeans","straight jeans","relaxed jeans",
               "wide leg jeans","cargo pants","chinos","trousers","dress pants","joggers",
               "sweatpants","track pants","leggings","palazzo pants","culottes","shorts",
               "denim shorts","cargo shorts","bermuda shorts","mini skirt","midi skirt",
               "maxi skirt","pleated skirt","pencil skirt","a-line skirt","denim skirt",
               "dhoti","lungi"]
    full_outfits = ["mini dress","midi dress","maxi dress","wrap dress","shirt dress",
                    "bodycon dress","slip dress","cocktail dress","evening gown","sundress",
                    "saree","lehenga","salwar kameez","anarkali"]
    footwear_types = ["sneakers","running shoes","walking shoes","basketball shoes",
                      "high top sneakers","low top sneakers","canvas shoes","formal shoes",
                      "oxfords","derbies","loafers","monk strap shoes","boots","chelsea boots",
                      "combat boots","hiking boots","sandals","flip flops","slippers",
                      "heels","pumps","wedges","flats","mules","trail runners"]
    g = gt.lower()
    if g in [t.lower() for t in tops]:           return "top"
    if g in [t.lower() for t in outerwear]:      return "outerwear"
    if g in [t.lower() for t in bottoms]:        return "bottom"
    if g in [t.lower() for t in full_outfits]:   return "full_outfit"
    if g in [t.lower() for t in footwear_types]: return "footwear"
    return "unknown"

def build_garment_object(clip_results, image_path, threshold=0.6):
    g = {
        "image_path": image_path,
        "garment_type": None, "primary_color": None, "secondary_color": None,
        "fabric": None, "pattern": None, "fit": None, "style": None,
        "occasion": None, "season": None, "footwear": None, "category": None,
        "confidence_scores": {}, "low_confidence_fields": []
    }
    field_map = {
        "garment_type":"garment_type","primary_color":"primary_color",
        "pattern":"pattern","fit":"fit","fabric":"fabric",
        "style":"style","occasion":"occasion","season":"season","footwear":"footwear"
    }
    for clip_cat, field in field_map.items():
        if clip_cat in clip_results and clip_results[clip_cat]:
            top = clip_results[clip_cat][0]
            g[field] = top["label"]
            g["confidence_scores"][field] = top["confidence"]
            if top["confidence"] / 100.0 < threshold:
                g["low_confidence_fields"].append(field)
    g["category"] = _derive_category(g["garment_type"])
    if "primary_color" in clip_results and len(clip_results["primary_color"]) > 1:
        g["secondary_color"] = clip_results["primary_color"][1]["label"]
    return g


# ── CELL 6: Upload images ────────────────────────────────────
print("\n" + "=" * 60)
print("  STEP 3: UPLOAD YOUR GARMENT PHOTOS")
print("=" * 60)

uploaded = files.upload()
image_paths = []
for filename, data in uploaded.items():
    path = os.path.join("wardrobe_images", filename)
    with open(path, "wb") as f:
        f.write(data)
    image_paths.append(path)
print(f"✅ {len(image_paths)} image(s) uploaded")


# ── CELL 7: Choose occasion ──────────────────────────────────

occasion = input(
    "\nChoose occasion:\n"
    "  everyday / office / college / party / date night\n"
    "  wedding / formal dinner / outdoor / gym / travel\n\n"
    "Enter occasion: "
).strip().lower()
print(f"✅ Occasion set: {occasion}")


# ── CELL 8: FULL END-TO-END RUN ──────────────────────────────

print("\n" + "=" * 60)
print("  STEP 4: RUNNING FULL PIPELINE")
print("=" * 60)

garment_objects = []

for path in image_paths:
    print(f"\n📷 {os.path.basename(path)}")

    # CLIP → raw predictions
    clip_results = run_clip_per_category(
        path, LABELS_DICT, clip_model, clip_processor, top_k=3
    )

    # Post-process → structured garment object
    garment = build_garment_object(clip_results, path)
    garment_objects.append(garment)

    print(f"   Garment   : {garment['garment_type']}  ({garment['confidence_scores'].get('garment_type',0):.1f}%)")
    print(f"   Color     : {garment['primary_color']}  ({garment['confidence_scores'].get('primary_color',0):.1f}%)")
    print(f"   Fabric    : {garment['fabric']}")
    print(f"   Pattern   : {garment['pattern']}")
    print(f"   Fit       : {garment['fit']}")
    print(f"   Style     : {garment['style']}")
    print(f"   Category  : {garment['category']}")
    if garment["low_confidence_fields"]:
        print(f"   ⚠️  Verify : {garment['low_confidence_fields']}")


# XGBoost scoring
print(f"\n{'─'*60}")
print("🔢 XGBoost Scoring...")

score, confidence, features = predict_outfit_score(
    garment_objects, occasion, xgb_reg, xgb_clf
)

print(f"\n{'='*60}")
print(f"  OCCASION            : {occasion}")
print(f"  GARMENTS ANALYSED   : {len(garment_objects)}")
print()
for feat, val in features.items():
    bar = "█" * int(val / 10)
    weight = SCORING_WEIGHTS.get(feat, 0)
    print(f"  {feat:<15} {val:>5.1f}  wt={weight:.2f}  {bar}")
print()
print(f"  COMPATIBILITY SCORE : {score} / 100")
print(f"  CONFIDENCE SCORE    : {confidence:.2f} / 1.0")

if confidence < 0.6:
    print(f"\n  ⚠️  Low confidence ({confidence:.2f}) — some attributes uncertain")

verdict = (
    "✅ Great outfit for this occasion"  if score >= 75 else
    "🟡 Decent — minor improvements possible" if score >= 55 else
    "🟠 Some issues — check color or fabric pairing" if score >= 35 else
    "❌ Poor match for this occasion"
)
print(f"\n  VERDICT  : {verdict}")
print(f"{'='*60}")

# Save garment objects as JSON for wardrobe DB (next step)
os.makedirs("wardrobe_db", exist_ok=True)
db_entry = {
    "occasion": occasion,
    "compatibility_score": score,
    "confidence_score": confidence,
    "features": features,
    "garments": [
        {k: v for k, v in g.items() if k != "confidence_scores"}
        for g in garment_objects
    ]
}
ts = int(__import__("time").time())
db_path = f"wardrobe_db/outfit_{ts}.json"
with open(db_path, "w") as f:
    json.dump(db_entry, f, indent=2)

print(f"\n✅ Outfit saved to: {db_path}")
print("   (This is the start of your Wardrobe Database — Req 2)")

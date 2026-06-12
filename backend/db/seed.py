import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import User, Wardrobe, Garment, GarmentOccasionTag

logger = logging.getLogger(__name__)

DEMO_GARMENTS = [
    {
        "garmentId": "65d4c67f-154a-4388-85a0-0f955d55bb65",
        "name": "Navy Blazer",
        "category": "outerwear",
        "primaryColor": "navy",
        "secondaryColor": "gray",
        "fabricType": "wool",
        "patternType": "solid",
        "fitType": "tailored fit",
        "styleTag": "smart casual",
        "imageUrl": "http://localhost:8000/static/uploads/navy_blazer.png",
        "occasionTags": ["business casual", "everyday", "formal", "wedding", "party"]
    },
    {
        "garmentId": "f3358373-77d5-4750-8ed6-667ef4643ae3",
        "name": "Beige Trench Coat",
        "category": "outerwear",
        "primaryColor": "beige",
        "secondaryColor": None,
        "fabricType": "cotton",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/beige_trench_coat.png",
        "occasionTags": ["casual", "travel", "date night", "everyday"]
    },
    {
        "garmentId": "7a796f8e-41fd-4f1d-99e7-d3706e2128a8",
        "name": "White Oxford Shirt",
        "category": "top",
        "primaryColor": "white",
        "secondaryColor": None,
        "fabricType": "cotton",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "classic",
        "imageUrl": "http://localhost:8000/static/uploads/white_shirt.png",
        "occasionTags": ["business casual", "casual", "everyday", "formal", "wedding", "party"]
    },
    {
        "garmentId": "0cd83792-2415-4384-8441-80bc2725d2f5",
        "name": "Charcoal Trousers",
        "category": "bottom",
        "primaryColor": "charcoal",
        "secondaryColor": None,
        "fabricType": "wool",
        "patternType": "solid",
        "fitType": "slim fit",
        "styleTag": "classic",
        "imageUrl": "http://localhost:8000/static/uploads/charcoal_trousers.png",
        "occasionTags": ["business casual", "everyday", "formal", "wedding"]
    },
    {
        "garmentId": "1c039046-e857-497a-a384-363c51a42c0a",
        "name": "Brown Derby Shoes",
        "category": "footwear",
        "primaryColor": "brown",
        "secondaryColor": None,
        "fabricType": "leather",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "classic",
        "imageUrl": "http://localhost:8000/static/uploads/brown_shoes.png",
        "occasionTags": ["business casual", "casual", "everyday", "formal", "wedding"]
    },
    {
        "garmentId": "6332614a-6e22-4509-a9c6-8da929b4f540",
        "name": "Khaki Chinos",
        "category": "bottom",
        "primaryColor": "khaki",
        "secondaryColor": None,
        "fabricType": "cotton",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/khaki_chinos.png",
        "occasionTags": ["business casual", "casual", "everyday", "travel"]
    },
    {
        "garmentId": "f0a11260-516a-402d-93bd-1b5993089ee9",
        "name": "Black Turtleneck",
        "category": "top",
        "primaryColor": "black",
        "secondaryColor": None,
        "fabricType": "cotton",
        "patternType": "solid",
        "fitType": "slim fit",
        "styleTag": "classic",
        "imageUrl": "http://localhost:8000/static/uploads/black_turtleneck.png",
        "occasionTags": ["casual", "date night", "everyday", "party"]
    },
    {
        "garmentId": "5c6d20bc-d061-403c-980f-19126073518c",
        "name": "Light Blue Denim Jacket",
        "category": "outerwear",
        "primaryColor": "blue",
        "secondaryColor": None,
        "fabricType": "denim",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/denim_jacket.png",
        "occasionTags": ["casual", "date night", "everyday", "festival", "party"]
    },
    {
        "garmentId": "8a97ca20-c8b7-4391-b726-44d67e8d77d2",
        "name": "Grey Crewneck Sweatshirt",
        "category": "top",
        "primaryColor": "gray",
        "secondaryColor": None,
        "fabricType": "cotton",
        "patternType": "solid",
        "fitType": "relaxed fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/grey_sweatshirt.png",
        "occasionTags": ["casual", "outdoor", "everyday", "sport", "travel", "festival"]
    },
    {
        "garmentId": "e2640196-54a6-4371-ba4e-ba51528d6774",
        "name": "Black Slim Jeans",
        "category": "bottom",
        "primaryColor": "black",
        "secondaryColor": None,
        "fabricType": "denim",
        "patternType": "solid",
        "fitType": "slim fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/black_jeans.png",
        "occasionTags": ["casual", "date night", "everyday", "festival", "party"]
    },
    {
        "garmentId": "8340fb5d-c768-4454-8f5d-c98e391fb0d0",
        "name": "White Leather Sneakers",
        "category": "footwear",
        "primaryColor": "white",
        "secondaryColor": None,
        "fabricType": "leather",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/white_sneakers.png",
        "occasionTags": ["casual", "sport", "everyday", "travel", "festival"]
    },
    {
        "garmentId": "5f5fc1db-7e22-43bc-a4fd-a7fb96bf77cc",
        "name": "Navy Merino V-Neck Sweater",
        "category": "top",
        "primaryColor": "navy",
        "secondaryColor": None,
        "fabricType": "wool",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "classic",
        "imageUrl": "http://localhost:8000/static/uploads/navy_sweater.png",
        "occasionTags": ["business casual", "formal", "everyday"]
    },
    {
        "garmentId": "1fa058b2-c865-4214-919e-d43b228530d4",
        "name": "Tan Leather Belt",
        "category": "accessory",
        "primaryColor": "brown",
        "secondaryColor": None,
        "fabricType": "leather",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "classic",
        "imageUrl": "http://localhost:8000/static/uploads/tan_belt.png",
        "occasionTags": ["business casual", "casual", "formal", "everyday", "wedding"]
    },
    {
        "garmentId": "73d5cbce-74aa-4fb1-9127-8aa0e0eb863b",
        "name": "Dark Green Cargo Pants",
        "category": "bottom",
        "primaryColor": "green",
        "secondaryColor": None,
        "fabricType": "cotton",
        "patternType": "solid",
        "fitType": "relaxed fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/cargo_pants.png",
        "occasionTags": ["casual", "outdoor", "everyday", "sport", "festival"]
    },
    {
        "garmentId": "67c95344-b59f-4203-a8da-fe7f699a67a6",
        "name": "Chelsea Boots",
        "category": "footwear",
        "primaryColor": "brown",
        "secondaryColor": None,
        "fabricType": "leather",
        "patternType": "solid",
        "fitType": "regular fit",
        "styleTag": "casual",
        "imageUrl": "http://localhost:8000/static/uploads/chelsea_boots.png",
        "occasionTags": ["casual", "date night", "everyday", "party"]
    }
]

async def seed_demo_data(db: AsyncSession):
    """Seed demo garments if the database is empty."""
    # Check if there are already any garments
    result = await db.execute(select(Garment))
    if result.scalars().first():
        logger.info("[Database] Garments already exist, skipping seeding.")
        return

    logger.info("[Database] Seeding 15 sample demo garments...")

    # Ensure demo-user exists
    user_result = await db.execute(select(User).where(User.userId == "demo-user"))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(userId="demo-user", email="demo-user@wardrobe.local", role="user")
        db.add(user)
        await db.flush()

    # Ensure wardrobe exists
    wardrobe_result = await db.execute(select(Wardrobe).where(Wardrobe.userId == "demo-user"))
    wardrobe = wardrobe_result.scalar_one_or_none()
    if not wardrobe:
        wardrobe = Wardrobe(wardrobeId="d4efdff1-54ef-4268-9e8e-79dd4c3aeaa9", userId="demo-user")
        db.add(wardrobe)
        await db.flush()

    for item in DEMO_GARMENTS:
        garment = Garment(
            garmentId=item["garmentId"],
            wardrobeId=wardrobe.wardrobeId,
            name=item["name"],
            category=item["category"],
            primaryColor=item["primaryColor"],
            secondaryColor=item["secondaryColor"],
            fabricType=item["fabricType"],
            patternType=item["patternType"],
            fitType=item["fitType"],
            styleTag=item["styleTag"],
            imageUrl=item["imageUrl"],
        )
        db.add(garment)
        await db.flush()

        for tag in item["occasionTags"]:
            db.add(GarmentOccasionTag(garmentId=garment.garmentId, tag=tag))
        await db.flush()

        # Update vector store
        try:
            from vector_store.store import get_vector_store
            garment_dict = {
                "garmentId": garment.garmentId,
                "name": garment.name,
                "category": garment.category,
                "primaryColor": garment.primaryColor,
                "fabricType": garment.fabricType,
                "fitType": garment.fitType or "",
                "styleTag": garment.styleTag or "",
                "occasionTags": item["occasionTags"],
            }
            vs = get_vector_store()
            vs.add_garment(garment_dict, "demo-user")
        except Exception as e:
            logger.error(f"[Database] Seeding vector store failed for {garment.garmentId}: {e}")

    await db.commit()
    logger.info("[Database] Seeding complete! 15 sample garments inserted.")

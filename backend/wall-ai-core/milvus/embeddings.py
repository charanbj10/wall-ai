from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_image(name: str, topic: str, hashtags: list) -> list[float]:
    """Image embedding — name + topic + hashtags"""
    text = f"{name} {topic} {' '.join(hashtags or [])}"
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_user_taste(taste: dict) -> list[float]:
    """
    User taste embedding — weighted by interaction history.
    taste = {
        "Watch": { "weight": 0.9, "names": ["Blue Watch", "Chain Watch"], "hashtags": ["WaterProof"] },
        "Shoes": { "weight": 0.1, "names": ["Red Shoe"], "hashtags": ["Running"] },
    }
    Builds rich text: "Watch Watch Watch Blue Watch Chain Watch WaterProof Shoes Red Shoe Running"
    """
    words = []
    for topic, data in taste.items():
        weight   = data.get("weight", 0.0)
        names    = data.get("names", [])
        hashtags = data.get("hashtags", [])

        if weight <= 0:
            continue

        # Repeat topic by weight — higher weight = more influence
        count = max(1, round(weight * 10))
        words.extend([topic] * count)

        # Add names and hashtags for richer context
        words.extend(names)
        words.extend(hashtags)

    text = " ".join(words) if words else "general"
    return model.encode(text, normalize_embeddings=True).tolist()
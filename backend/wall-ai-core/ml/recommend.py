import sys
import os
import pickle
import numpy as np
from db.database import SessionLocal
from db.models import Download

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from milvus.client import get_users_collection, get_images_collection

MODEL_PATH = "ml/kmeans_model.pkl"

# ─────────────────────────────────────────
# LOAD K-MEANS MODEL
# ─────────────────────────────────────────
def load_model():
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print("[Recommend] No K-Means model found — using hybrid strategy")
        return None


# ─────────────────────────────────────────
# FETCH USER FROM MILVUS
# ─────────────────────────────────────────
def get_user(user_id: str) -> dict | None:
    """
    Fetch user embedding + cluster_id from Milvus.
    Returns None if user not found (new user → cold start).
    """
    col = get_users_collection()
    results = col.query(
        expr=f'user_id == "{user_id}"',
        output_fields=["user_id", "embedding", "cluster_id"],
        limit=1,
    )
    return results[0] if results else None


# ─────────────────────────────────────────
# STRATEGY 1 — COLD START
# New user — no taste data yet
# Return most popular / recent images
# ─────────────────────────────────────────
def cold_start(limit: int, topic: str = None) -> list[dict]:
    """
    For new users with no interaction history.
    Returns all images filtered by topic if provided.
    """
    col   = get_images_collection()
    expr  = f'topic == "{topic}"' if topic else "image_id != ''"

    results = col.query(
        expr=expr,
        output_fields=["image_id", "topic", "name", "hashtags"],
        limit=limit,
    )

    print(f"[Recommend] Cold start — returning {len(results)} images")
    return results



def get_interaction_count(user_id: str) -> int:
    """
    Count how many downloads/views this user has had.
    Read from PostgreSQL downloads table.
    """
    db = SessionLocal()


    count = db.query(Download).filter(
        Download.uid == user_id
    ).count()
    return count
# ─────────────────────────────────────────
# STRATEGY 2 — COLLABORATIVE (K-Means)
# Find users in same cluster → use cluster
# centroid as search vector in Milvus
# ─────────────────────────────────────────
def collaborative(
    user_embedding: list[float],
    cluster_id: int,
    limit: int,
    topic: str = None,
) -> list[dict]:
    """
    Uses K-Means cluster centroid to find images.
    All users in same cluster get similar recommendations.
    """
    kmeans = load_model()

    if kmeans is not None:
        # Use cluster centroid as the search vector
        # Centroid = average taste of all users in this cluster
        search_vector = kmeans.cluster_centers_[cluster_id].tolist()
        print(f"[Recommend] Using cluster {cluster_id} centroid as search vector")
    else:
        # Fallback — use user's own embedding
        search_vector = user_embedding
        print(f"[Recommend] No model — using user embedding directly")

    return search_milvus(search_vector, limit, topic)


# ─────────────────────────────────────────
# STRATEGY 3 — HYBRID
# Blend user embedding + cluster centroid
# Best of both worlds
# ─────────────────────────────────────────
def hybrid(
    user_embedding: list[float],
    cluster_id: int,
    limit: int,
    topic: str = None,
    user_weight: float = 0.4,
    cluster_weight: float = 0.6,
) -> list[dict]:
    """
    Blends user's personal embedding with cluster centroid.
    cluster_weight=0.6 means 60% cluster taste, 40% personal taste.
    """
    kmeans = load_model()

    if kmeans is not None:
        centroid = np.array(kmeans.cluster_centers_[cluster_id])
        user_emb = np.array(user_embedding)

        # Weighted blend
        blended = (user_weight * user_emb) + (cluster_weight * centroid)

        # Normalise blended vector
        norm = np.linalg.norm(blended)
        if norm > 0:
            blended = blended / norm

        search_vector = blended.tolist()
        print(f"[Recommend] Hybrid — {user_weight*100}% personal + {cluster_weight*100}% cluster")
    else:
        search_vector = user_embedding
        print(f"[Recommend] Hybrid fallback — using user embedding only")

    return search_milvus(search_vector, limit, topic)


# ─────────────────────────────────────────
# MILVUS VECTOR SEARCH
# ─────────────────────────────────────────
def search_milvus(
    vector: list[float],
    limit: int,
    topic: str = None,
) -> list[dict]:
    """
    Searches Milvus images collection for most similar images.
    Optionally filters by topic.
    """
    col  = get_images_collection()
    expr = f'topic == "{topic}"' if topic else None

    results = col.search(
        data=[vector],                              # search vector
        anns_field="embedding",                     # field to search
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=limit,
        expr=expr,                                  # optional topic filter
        output_fields=["image_id", "topic", "name", "hashtags"],
    )

    # Flatten results — search returns nested list
    images = []
    for hits in results:
        for hit in hits:
            images.append({
                "image_id":  hit.entity.get("image_id"),
                "topic":     hit.entity.get("topic"),
                "name":      hit.entity.get("name"),
                "hashtags":  hit.entity.get("hashtags"),
                "score":     round(hit.score, 4),   # similarity score 0-1
            })

    print(f"[Recommend] Found {len(images)} images from Milvus")
    return images


# ─────────────────────────────────────────
# MAIN RECOMMEND FUNCTION
# Called from FastAPI endpoint
# ─────────────────────────────────────────
def recommend(
    user_id: str,
    limit: int = 20,
    topic: str = None,
) -> dict:
    """
    Main recommendation function.
    Automatically picks best strategy based on user data.

    Returns:
    {
        "user_id":   "uuid",
        "strategy":  "cold_start | collaborative | hybrid",
        "cluster_id": 0,
        "images":    [ { image_id, topic, name, hashtags, score } ]
    }
    """
    print(f"\n[Recommend] Request — user: {user_id[:8]}... | limit: {limit} | topic: {topic}")

    # Fetch user from Milvus
    user = get_user(user_id)

    # ── COLD START — new user, no data ──
    if user is None:
        print("[Recommend] Strategy: cold_start (new user)")
        images = cold_start(limit, topic)
        return {
            "user_id":    user_id,
            "strategy":   "cold_start",
            "cluster_id": -1,
            "images":     images,
        }

    user_embedding = user["embedding"]
    cluster_id     = user.get("cluster_id", 0)

    # Count how many interactions user has had
    interaction_count = get_interaction_count(user_id)

    # Few interactions → hybrid (personal + cluster)
    if interaction_count < 10:
        print(f"[Recommend] Strategy: hybrid | cluster: {cluster_id}")
        images = hybrid(user_embedding, cluster_id, limit, topic)
        return {
            "user_id":    user_id,
            "strategy":   "hybrid",
            "cluster_id": cluster_id,
            "images":     images,
        }

    # Many interactions → pure collaborative
    # User's taste is well established
    # Trust the cluster more than personal vector
    images = collaborative(user_embedding, cluster_id, limit, topic)
    return {
        "user_id":    user_id,
        "strategy":   "collaborative",
        "cluster_id": cluster_id,
        "images":     images,
    }


# ─────────────────────────────────────────
# TEST — run directly
# cd wall-ai-core
# python ml/recommend.py
# ─────────────────────────────────────────
if __name__ == "__main__":
    # Test with your actual user_id
    result = recommend(
        user_id = "8689ed4e-0bdb-4ef7-ac96-97ba848a8293",
        limit   = 5,
    )

    print("\n[Recommend] Results:")
    print(f"  Strategy  : {result['strategy']}")
    print(f"  Cluster   : {result['cluster_id']}")
    print(f"  Images    : {len(result['images'])}")
    for img in result["images"]:
        print(f"    [{img['score']}] {img['name']} — {img['topic']}")
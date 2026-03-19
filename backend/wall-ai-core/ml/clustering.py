import sys
import os
import pickle
import numpy as np
from sklearn.cluster import KMeans

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from milvus.client import get_users_collection

# ─────────────────────────────────────────
# CONFIG
# Increase N_CLUSTERS as more users join:
# 2-10 users   → 2 clusters
# 10-50 users  → 4 clusters
# 50+ users    → 8 clusters
# ─────────────────────────────────────────
MIN_USERS_PER_CLUSTER = 1   # at least 1 user per cluster
MODEL_PATH = "ml/kmeans_model.pkl"


def get_n_clusters(total_users: int) -> int:
    """Dynamically decide cluster count based on user count."""
    if total_users <= 2:   return 2
    if total_users <= 10:  return 3
    if total_users <= 50:  return 5
    return 8


def fetch_user_embeddings() -> tuple[list[str], np.ndarray]:
    """
    Reads all user embeddings from Milvus users collection.
    Returns:
        user_ids   → ["uuid-1", "uuid-2", ...]
        embeddings → numpy array shape (n_users, 384)
    """
    col = get_users_collection()

    # Query all users — get user_id and embedding fields
    results = col.query(
        expr="user_id != ''",         # get all users
        output_fields=["user_id", "embedding"],
        limit=10000,                  # max users to fetch
    )

    if not results:
        print("[Clustering] No users found in Milvus")
        return [], np.array([])

    user_ids   = [r["user_id"]   for r in results]
    embeddings = np.array([r["embedding"] for r in results])

    print(f"[Clustering] Fetched {len(user_ids)} users from Milvus")
    return user_ids, embeddings


def run_kmeans(embeddings: np.ndarray, n_clusters: int) -> KMeans:
    """
    Runs K-Means on user embeddings.
    Returns trained KMeans model.
    """
    print(f"[Clustering] Running K-Means with {n_clusters} clusters...")

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10,         # run 10 times, pick best
        max_iter=300,
    )
    kmeans.fit(embeddings)

    print(f"[Clustering] Done! Inertia: {kmeans.inertia_:.4f}")
    return kmeans


def save_cluster_ids(user_ids: list[str], cluster_ids: list[int]):
    """
    Saves cluster_id back to each user in Milvus.
    Uses upsert — updates existing user records.
    """
    col = get_users_collection()

    # Fetch current embeddings to preserve them during upsert
    results = col.query(
        expr="user_id != ''",
        output_fields=["user_id", "embedding"],
        limit=10000,
    )
    emb_map = {r["user_id"]: r["embedding"] for r in results}

    # Upsert with updated cluster_ids
    upsert_user_ids   = []
    upsert_embeddings = []
    upsert_clusters   = []

    for uid, cid in zip(user_ids, cluster_ids):
        if uid in emb_map:
            upsert_user_ids.append(uid)
            upsert_embeddings.append(emb_map[uid])
            upsert_clusters.append(int(cid))

    col.upsert([upsert_user_ids, upsert_embeddings, upsert_clusters])
    col.flush()
    print(f"[Clustering] Saved cluster_ids for {len(upsert_user_ids)} users")


def save_model(kmeans: KMeans):
    """Save trained K-Means model to disk for use in recommendation."""
    os.makedirs("ml", exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(kmeans, f)
    print(f"[Clustering] Model saved → {MODEL_PATH}")


def load_model() -> KMeans | None:
    """Load saved K-Means model — used by recommendation engine."""
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        print(f"[Clustering] Model loaded from {MODEL_PATH}")
        return model
    except FileNotFoundError:
        print("[Clustering] No saved model found — run clustering first")
        return None


def run_clustering():
    """
    Full clustering pipeline:
    1. Fetch user embeddings from Milvus
    2. Run K-Means
    3. Save cluster_id back to Milvus
    4. Save model to disk
    """
    print("\n[Clustering] Starting K-Means clustering...")
    print("=" * 50)

    # Step 1 — fetch embeddings
    user_ids, embeddings = fetch_user_embeddings()

    if len(user_ids) == 0:
        print("[Clustering] No users to cluster. Add more users first.")
        return

    # Step 2 — decide cluster count
    n_clusters = get_n_clusters(len(user_ids))
    print(f"[Clustering] {len(user_ids)} users → {n_clusters} clusters")

    # Step 3 — run K-Means
    kmeans = run_kmeans(embeddings, n_clusters)

    # Step 4 — print cluster assignments
    cluster_ids = kmeans.labels_.tolist()
    print("\n[Clustering] Results:")
    for uid, cid in zip(user_ids, cluster_ids):
        print(f"  User {uid[:8]}... → Cluster {cid}")

    # Step 5 — save cluster_ids back to Milvus
    save_cluster_ids(user_ids, cluster_ids)

    # Step 6 — save model for recommendation engine
    save_model(kmeans)

    print("\n[Clustering] Done!")
    print(f"  Users clustered : {len(user_ids)}")
    print(f"  Clusters created: {n_clusters}")
    print(f"  Model saved at  : {MODEL_PATH}")
    print("=" * 50)


# ─────────────────────────────────────────
# Run directly:
#   cd wall-ai-core
#   python ml/clustering.py
# ─────────────────────────────────────────
if __name__ == "__main__":
    run_clustering()
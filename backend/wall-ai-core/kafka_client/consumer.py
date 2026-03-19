import json
import sys
import os
import threading
from collections import defaultdict
from datetime import datetime
from kafka import KafkaConsumer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import Image
from milvus.client import get_users_collection
from milvus.embeddings import embed_user_taste

# ─────────────────────────────────────────
# TOPICS — fetched from PostgreSQL
# ─────────────────────────────────────────
def fetch_topics() -> list[str]:
    db = SessionLocal()
    try:
        rows = db.query(Image.topic).distinct().all()
        topics = [row[0] for row in rows if row[0] is not None]
        print(f"[Consumer] Topics loaded from DB: {topics}")
        return topics
    except Exception as e:
        print(f"[Consumer] Failed to fetch topics, using fallback: {e}")
        return ["Watch", "Shoes", "TV", "Tshirt", "Shirt", "Pant", "Fridge"]
    finally:
        db.close()

TOPICS = fetch_topics()

# ─────────────────────────────────────────
# EVENT WEIGHTS
# download = strong signal
# view     = weak signal
# ─────────────────────────────────────────
EVENT_WEIGHTS = {
    "download": 1.0,
    "view":     0.1,
}

# ─────────────────────────────────────────
# IN-MEMORY TASTE STORE
# { user_id: { "Watch": 0.9, "Shoes": 0.1 ... } }
# ─────────────────────────────────────────
taste_store: dict[str, dict[str, float]] = defaultdict(
    lambda: {t: 0.0 for t in TOPICS}
)

_running = True


# ─────────────────────────────────────────
# TASTE VECTOR UPDATE
# ─────────────────────────────────────────
def update_taste(user_id: str, topic: str, event_type: str,
                 name: str = "", hashtags: list = []):
    """
    Updates user taste with full image context.
    """
    weight = EVENT_WEIGHTS.get(event_type, 0.1)

    # Init user if new
    if user_id not in taste_store:
        taste_store[user_id] = {}

    # Init topic if new
    if topic not in taste_store[user_id]:
        taste_store[user_id][topic] = {
            "weight":   0.0,
            "names":    [],
            "hashtags": [],
        }

    # Decay all topic weights
    for t in taste_store[user_id]:
        taste_store[user_id][t]["weight"] *= 0.95

    # Boost this topic weight
    taste_store[user_id][topic]["weight"] += weight

    # Add name if not already in list
    if name and name not in taste_store[user_id][topic]["names"]:
        taste_store[user_id][topic]["names"].append(name)

    # Add new hashtags
    for h in (hashtags or []):
        if h and h not in taste_store[user_id][topic]["hashtags"]:
            taste_store[user_id][topic]["hashtags"].append(h)

    # Normalise weights
    total = sum(v["weight"] for v in taste_store[user_id].values())
    if total > 0:
        for t in taste_store[user_id]:
            taste_store[user_id][t]["weight"] = round(
                taste_store[user_id][t]["weight"] / total, 4
            )

    print(f"[Consumer] Taste updated — {user_id[:8]}... | {topic} | {event_type}")
    print(f"[Consumer] Vector: { {t: v['weight'] for t, v in taste_store[user_id].items()} }")


# ─────────────────────────────────────────
# MILVUS UPSERT
# ─────────────────────────────────────────
def upsert_user_milvus(user_id: str):
    """
    Embeds user taste vector and upserts into Milvus users collection.
    Schema: user_id (varchar), embedding (float 384), cluster_id (int)
    cluster_id = 0 until K-Means runs
    """
    try:
        taste  = taste_store[user_id]
        embedding    = embed_user_taste(taste)
        col    = get_users_collection()

        col.upsert([
            [user_id],   # user_id
            [embedding],       # embedding 384-dim
            [0],         # cluster_id — updated later by K-Means
        ])
        col.flush()
        print(f"[Consumer] Milvus upserted — user: {user_id[:8]}...")

    except Exception as e:
        print(f"[Consumer] Milvus upsert failed: {e}")


# ─────────────────────────────────────────
# PROCESS ONE EVENT
# ─────────────────────────────────────────
def process_event(msg: dict):
    user_id    = msg.get("user_id")
    topic      = msg.get("topic")
    event_type = msg.get("event", "download")
    name       = msg.get("name", "")           # ← now used
    hashtags   = msg.get("hashtags", [])       # ← now used

    if not user_id or not topic:
        return

    # Pass full context to taste update
    update_taste(user_id, topic, event_type, name, hashtags)
    upsert_user_milvus(user_id)



# ─────────────────────────────────────────
# CONSUMER LOOP
# Listens to BOTH topics in one consumer
# ─────────────────────────────────────────
def run_consumer():
    print("[Consumer] Connecting to Kafka...")
    try:
        consumer = KafkaConsumer(
            "wallai-downloads",   # topic 1 — download events
            "wallai-views",       # topic 2 — view events
            bootstrap_servers="localhost:9093",  # external port
            group_id="wallai-recommendation-group",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            consumer_timeout_ms=1000,  # allows checking _running flag
        )
        print("[Consumer] Listening on wallai-downloads + wallai-views...")

        while _running:
            for message in consumer:
                if not _running:
                    break
                print(f"\n[Consumer] [{message.topic}] {message.value}")
                process_event(message.value)

        consumer.close()
        print("[Consumer] Stopped.")

    except Exception as e:
        print(f"[Consumer] Error: {e}")


# ─────────────────────────────────────────
# START / STOP — called from main.py
# ─────────────────────────────────────────
def start_consumer():
    """Start consumer in background thread — call on FastAPI startup."""
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()
    print("[Consumer] Background thread started")


def stop_consumer():
    """Stop consumer — call on FastAPI shutdown."""
    global _running
    _running = False
    print("[Consumer] Shutting down...")


# ─────────────────────────────────────────
# TEST — run directly
# python kafka_client/consumer.py
# Then in another terminal: python kafka_client/producer.py
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("Starting consumer — waiting for events...")
    print("In another terminal run: python kafka_client/producer.py")
    _running = True
    run_consumer()
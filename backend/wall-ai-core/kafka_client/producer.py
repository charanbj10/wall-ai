import json
from datetime import datetime
from kafka import KafkaProducer

TOPIC_DOWNLOADS = "wallai-downloads"
TOPIC_VIEWS     = "wallai-views"

# ─────────────────────────────────────────
# LAZY PRODUCER
# Created on first use — not at import time
# Prevents startup crash if Kafka not ready
# ─────────────────────────────────────────
_producer = None

def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers="localhost:9093",
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            request_timeout_ms=5000,
            max_block_ms=5000,
        )
        print("[Producer] Kafka connected")
    return _producer


def send_download_event(user_id: str, image_id: str, topic: str, hashtags: list, name: str):
    """
    Called when user downloads an image.
    Sends event to Kafka topic "wallai-downloads".
    """
    event = {
        "user_id":   user_id,
        "image_id":  image_id,
        "topic":     topic,
        "hashtags":  hashtags,
        "name":      name,
        "event":     "download",
        "timestamp": datetime.utcnow().isoformat(),
    }
    get_producer().send(
        topic=TOPIC_DOWNLOADS,
        key=user_id,
        value=event,
    )
    get_producer().flush()
    print(f"[Producer] Sent download event: {event}")


def send_view_event(user_id: str, image_id: str, topic: str, hashtags: list, name: str):
    """
    Called when user views an image.
    Weaker signal than download.
    """
    event = {
        "user_id":   user_id,
        "image_id":  image_id,
        "topic":     topic,
        "hashtags":  hashtags,
        "name":      name,
        "event":     "view",
        "timestamp": datetime.utcnow().isoformat(),
    }
    get_producer().send(
        topic=TOPIC_VIEWS,
        key=user_id,
        value=event,
    )
    get_producer().flush()
    print(f"[Producer] Sent view event: {event}")


# ─────────────────────────────────────────
# TEST — python kafka_client/producer.py
# Check http://localhost:8080 → Topics
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Kafka producer...")

    send_download_event(
        user_id  = "8689ed4e-0bdb-4ef7-ac96-97ba848a8293",
        image_id = "1",
        topic    = "Watch",
        hashtags = ["Blue", "WaterProof"],
        name     = "Blue Watch",
    )

    send_view_event(
        user_id  = "8689ed4e-0bdb-4ef7-ac96-97ba848a8293",
        image_id = "2",
        topic    = "Shoes",
        hashtags = ["Blue", "Running"],
        name     = "Blue Shoes",
    )

    print("Done! Check http://localhost:8080 → Topics → wallai-downloads")
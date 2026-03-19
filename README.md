# WallAI — AI-Powered Image Discovery Platform

> A Pinterest-style image discovery platform with real-time personalised recommendations powered by **Kafka event streaming**, **K-Means clustering**, **Milvus vector database**.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [How Recommendations Work](#how-recommendations-work)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Endpoints](#api-endpoints)
- [Infrastructure Setup](#infrastructure-setup)
- [AWS Deployment](#aws-deployment)

---

## Overview

WallAI is a full-stack image discovery platform where users can browse, upload, and download images. The platform learns from every user interaction in real time and serves personalised recommendations using an AI pipeline built from scratch.

**The core idea:**
- Every download/view is streamed as an event via **Kafka**
- Events update the user's **taste vector** (what they like)
- **K-Means clustering** groups users with similar tastes
- **Milvus vector DB** finds images matching the user's cluster
- Recommendations improve automatically as more users interact

---

## System Architecture

```
User Action (Download / View)
           ↓
    FastAPI Backend
           ↓
   Kafka Producer → [wallai-downloads topic]
                              ↓
                    Kafka Consumer (background thread)
                              ↓
                   Update User Taste Vector (in-memory)
                              ↓
                   Embed Taste → 384-dim vector
                   (SentenceTransformer: all-MiniLM-L6-v2)
                              ↓
                   Upsert to Milvus Users Collection
                              ↓
                    K-Means Clustering
                    Groups users by taste similarity
                              ↓
              GET /recommend/{user_id}
                              ↓
              Load user cluster → centroid vector
                              ↓
              Milvus similarity search on images
                              ↓
              Personalised feed returned to Frontend
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | FastAPI (Python) | REST API |
| Database | PostgreSQL + SQLAlchemy | Users, images, downloads |
| Event Streaming | Apache Kafka | Real-time user events |
| Vector Database | Milvus | Image + user embeddings |
| ML / AI | scikit-learn K-Means | User clustering |
| Embeddings | SentenceTransformer | 384-dim vector generation |
| Storage | AWS S3 | Image storage |
| Infrastructure | Docker Compose | Local dev environment |

---

## Features

### Core
- User signup / signin with JWT authentication
- Upload images → stored on **AWS S3** automatically
- Browse images by topic, hashtag, or search
- Download images with history tracking

### AI Recommendation Engine
- **Cold start** — new users see trending images
- **Hybrid strategy** — blend of personal taste + cluster centroid
- **Collaborative filtering** — users in same cluster see similar recommendations
- Real-time taste vector updates via Kafka

### Infrastructure
- Full event streaming pipeline with Kafka
- Vector similarity search with Milvus
- Kafka UI dashboard (`localhost:8080`)
- Attu (Milvus dashboard) (`localhost:3000`)

---

## How Recommendations Work

### Step 1 — Image Indexing (one time)
```bash
python milvus/indexer.py
```
Reads all images from PostgreSQL → generates 384-dim embeddings using SentenceTransformer → stores in Milvus images collection.

```
"Blue Watch Watch WaterProof Blue" → [0.12, 0.45, -0.23, ...]
```

### Step 2 — Real-time User Taste Update (every interaction)
```
User downloads "Blue Watch"
        ↓
Kafka event: { user_id, topic: "Watch", name: "Blue Watch" }
        ↓
Consumer updates taste vector:
{
  "Watch": { weight: 0.9, names: ["Blue Watch"], hashtags: ["WaterProof"] },
  "Shoes": { weight: 0.1, names: ["Red Shoe"],   hashtags: ["Running"] }
}
        ↓
Embed taste → 384-dim vector → upsert to Milvus
```

**Decay factor (0.95):** Old preferences fade over time so recent behaviour matters more.

### Step 3 — K-Means Clustering (nightly)
```bash
python ml/clustering.py
```
Reads all user embeddings → K-Means groups similar users → saves `cluster_id` back to Milvus + saves `kmeans_model.pkl`.

### Step 4 — Recommendation (every request)
```
GET /recommend/{user_id}
        ↓
Load user embedding + cluster_id from Milvus
        ↓
Get cluster centroid from kmeans_model.pkl
("average taste of all users in this cluster")
        ↓
Blend: 40% personal taste + 60% cluster centroid
        ↓
Milvus cosine similarity search on images
        ↓
Return top 20 most similar images
```

---

## Project Structure

```
WALL-AI/
├── wall-ai-core/                   ← FastAPI Backend
│   ├── main.py                     ← App entry point + lifespan
│   ├── requirements.txt
│   ├── .env
│   ├── db/
│   │   ├── database.py             ← SQLAlchemy connection
│   │   └── models.py               ← User, Image, Download models
│   ├── routers/
│   │   ├── auth.py                 ← POST /auth/signup, /auth/signin
│   │   ├── images.py               ← GET/POST /images/
│   │   ├── downloads.py            ← POST/GET /downloads/
│   │   └── recommend.py            ← GET /recommend/{user_id}
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── image_service.py
│   │   └── download_service.py
│   ├── kafka_client/
│   │   ├── producer.py             ← Sends events to Kafka
│   │   └── consumer.py             ← Reads events, updates taste vectors
│   ├── milvus/
│   │   ├── client.py               ← Milvus connection helper
│   │   ├── embeddings.py           ← SentenceTransformer embedding logic
│   │   └── indexer.py              ← Index images from PostgreSQL → Milvus
│   └── ml/
│       ├── clustering.py           ← K-Means clustering script
│       └── recommend.py            ← Recommendation engine
│
├── wallai-frontend/                ← Vanilla JS Frontend
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── config.js               ← BASE_URL config
│       ├── api.js                  ← HTTP helper + Bearer token
│       ├── auth.js                 ← Signup, signin, logout
│       ├── images.js               ← Grid, recommendations, search
│       ├── downloads.js            ← Download + history
│       ├── upload.js               ← File → base64 → S3 upload
│       ├── ui.js                   ← Toast, skeletons, likes
│       └── app.js                  ← Boot + event listeners
│
└── docker-compose-infra.yml        ← Kafka + Milvus + Redis
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Docker Desktop
- AWS Account (free tier)

### 1. Clone the repo
```bash
git clone https://github.com/charanbj10/wall-ai.git
cd wall-ai
```

### 2. Start infrastructure
```bash
docker-compose -f docker-compose-infra.yml up -d
```

This starts:
- Kafka broker (`localhost:9093` external, `localhost:9092` internal)
- Kafka UI (`localhost:8080`)
- Milvus vector DB (`localhost:19530`)
- Attu / Milvus dashboard (`localhost:3000`)

### 3. Setup backend
```bash
cd wall-ai-core
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Fill in:
# DATABASE_URL=postgresql://user:pass@localhost:5432/wallai
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_S3_BUCKET=your-bucket-name
# AWS_REGION=ap-south-1
# SECRET_KEY=your-jwt-secret
```

### 5. Index existing images into Milvus
```bash
python milvus/indexer.py
```

### 6. Start FastAPI
```bash
python -m uvicorn main:app --reload
```

API docs available at: `http://localhost:8000/docs`

### 7. Run frontend
```bash
cd wallai-frontend
python -m http.server 8001
```

Open: `http://localhost:8001`

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/signin` | Login → returns JWT token |

### Images
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/images/` | Browse images (topic, search, skip, limit) | No |
| GET | `/images/{image_id}` | Get single image + triggers Kafka view event | Optional |
| POST | `/images/upload` | Upload image (base64 → S3) | Yes |

### Downloads
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/downloads/` | Record download + Kafka event | Yes |
| GET | `/downloads/me` | My download history | Yes |

### Recommendations
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/recommend/{user_id}` | Personalised recommendations | Yes |

---

## Infrastructure Setup

### Milvus Collections

**images collection:**
```
image_id   → VARCHAR (primary key)
embedding  → FLOAT VECTOR[384]
topic      → VARCHAR
name       → VARCHAR
hashtags   → VARCHAR
```

**users collection:**
```
user_id    → VARCHAR (primary key)
embedding  → FLOAT VECTOR[384]
cluster_id → INT
```

### Kafka Topics
```
wallai-downloads  ← download events
wallai-views      ← view events
```

### K-Means Configuration
```python
N_CLUSTERS = 2    # increases automatically as users grow
DECAY      = 0.95 # taste vector decay factor
```

---

## AWS Deployment

### S3 Setup
```
Bucket name : your-bucket-name
Region      : ap-south-1
ACL         : Public read enabled
Policy      : s3:GetObject for *
```

Install Docker

```bash
git clone https://github.com/charanbj10/wall-ai.git
cd wallai
docker-compose -f docker-compose-infra.yml up -d
cd wall-ai-core && pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Resume Bullets

```
• Built a real-time image discovery platform with personalised AI recommendations
  using Kafka event streaming, K-Means clustering, and Milvus vector database

• Designed end-to-end recommendation pipeline: user interactions → Kafka events →
  taste vector updates → nightly K-Means clustering → cosine similarity search

• Implemented 384-dim sentence embeddings (SentenceTransformer) for both images
  and user taste profiles with exponential decay for recency bias

• Deployed FastAPI backend on AWS EC2 with image storage on S3, processing
  real-time events across Kafka topics with background consumer threads

• Stack: FastAPI · PostgreSQL · Apache Kafka · Milvus · K-Means ·
         SentenceTransformer · AWS EC2/S3 · Docker · Vanilla JS
```

---

## Skills Demonstrated

`Apache Kafka` `Milvus Vector DB` `K-Means Clustering` `SentenceTransformer`
`FastAPI` `PostgreSQL` `SQLAlchemy` `AWS S3` `AWS EC2` `Docker` `JWT Auth`
`Real-time event streaming` `Vector similarity search` `Recommendation systems`
`Python` `REST API design` `Vanilla JavaScript` `Pinterest-style UI`

---

## Author

**Sri Charan B J**  
[GitHub](https://github.com/charanbj10) · [LinkedIn](https://linkedin.com/in/charanbj)
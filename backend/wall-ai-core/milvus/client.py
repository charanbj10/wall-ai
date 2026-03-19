from pymilvus import connections, Collection, utility

def connect_milvus():
    connections.connect(alias="default", host="localhost", port="19530")

def get_images_collection() -> Collection:
    connect_milvus()
    col = Collection("images")

    if len(col.indexes) == 0:
        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200}
        }

        col.create_index(
            field_name="embedding",
            index_params=index_params
        )

    col.load()
    return col

def get_users_collection() -> Collection:
    connect_milvus()
    col = Collection("users")

    if len(col.indexes) == 0:
        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200}
        }

        col.create_index(
            field_name="embedding",
            index_params=index_params
        )

    col.load()
    return col
from apps.memory_api.core.contract import (
    CacheContract,
    DataType,
    EntityContract,
    FieldContract,
    MemoryContract,
    VectorCollectionContract,
    VectorStoreContract,
)

# Based on apps/memory_api/repositories/memory_repository.py and alembic migrations
RAE_MEMORY_CONTRACT_V1 = MemoryContract(
    version="1.0.0",
    entities=[
        EntityContract(
            name="memories",
            fields=[
                FieldContract(name="id", data_type=DataType.UUID, is_primary_key=True),
                FieldContract(name="tenant_id", data_type=DataType.UUID),
                FieldContract(name="content", data_type=DataType.TEXT),
                FieldContract(name="source", data_type=DataType.TEXT),
                FieldContract(name="importance", data_type=DataType.FLOAT),
                FieldContract(name="layer", data_type=DataType.TEXT),
                FieldContract(
                    name="tags", data_type=DataType.ARRAY_TEXT, nullable=True
                ),
                FieldContract(name="timestamp", data_type=DataType.TIMESTAMP),
                FieldContract(name="project", data_type=DataType.TEXT),
                FieldContract(name="memory_type", data_type=DataType.TEXT),
                FieldContract(
                    name="session_id", data_type=DataType.TEXT, nullable=True
                ),
                FieldContract(name="metadata", data_type=DataType.JSONB, nullable=True),
                FieldContract(name="created_at", data_type=DataType.TIMESTAMP),
                FieldContract(name="last_accessed_at", data_type=DataType.TIMESTAMP),
                FieldContract(name="usage_count", data_type=DataType.INTEGER),
                FieldContract(name="strength", data_type=DataType.FLOAT, nullable=True),
                FieldContract(
                    name="embedding",
                    data_type=DataType.VECTOR,
                    dimension=384,
                    nullable=True,
                ),
            ],
        )
    ],
    cache=CacheContract(required_namespaces=["rae:"]),
    vector_store=VectorStoreContract(
        collections=[
            VectorCollectionContract(
                name="memories", vector_size=384, distance_metric="Cosine"
            )
        ]
    ),
)

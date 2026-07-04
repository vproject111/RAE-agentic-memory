from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class DataType(str, Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    JSONB = "JSONB"
    VECTOR = "VECTOR"
    UUID = "UUID"
    ARRAY_TEXT = "ARRAY_TEXT"


class FieldContract(BaseModel):
    name: str
    data_type: DataType
    nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    has_index: bool = False
    dimension: Optional[int] = None  # For VECTOR type


class EntityContract(BaseModel):
    name: str
    fields: List[FieldContract]


class CacheContract(BaseModel):
    required_namespaces: List[str]


class VectorCollectionContract(BaseModel):
    name: str
    vector_size: int
    distance_metric: str = "Cosine"


class VectorStoreContract(BaseModel):
    collections: List[VectorCollectionContract]


class MemoryContract(BaseModel):
    """
    Defines the abstract memory structure required by RAE.
    Backend adapters must validate that their storage conforms to this contract.
    """

    version: str
    entities: List[EntityContract]
    cache: Optional[CacheContract] = None
    vector_store: Optional[VectorStoreContract] = None


class ValidationViolation(BaseModel):
    entity: str
    issue_type: str  # MISSING_TABLE, MISSING_COLUMN, TYPE_MISMATCH, etc.
    details: str


class ValidationResult(BaseModel):
    valid: bool
    violations: List[ValidationViolation]

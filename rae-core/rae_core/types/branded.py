from __future__ import annotations

import re
from typing import Annotated, NewType, TypeAlias

from pydantic import AfterValidator, BeforeValidator, StringConstraints


BinaryPayload: TypeAlias = bytes | bytearray | memoryview


def _normalize_non_empty(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("Wartość musi być tekstem")
    normalized = value.strip()
    if not normalized:
        raise ValueError("Wartość nie może być pusta")
    return normalized


def _validate_sha256(value: object) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    normalized = _normalize_non_empty(value).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("Checksum musi być 64-znakowym hashem SHA-256")
    return normalized


_ALLOWED_DATA_CLASSIFICATIONS = frozenset(
    {"public", "internal", "confidential", "restricted"}
)


def _validate_data_classification(value: object) -> str:
    normalized = _normalize_non_empty(value).lower()
    if normalized not in _ALLOWED_DATA_CLASSIFICATIONS:
        raise ValueError("Niepoprawna klasyfikacja danych")
    return normalized


KnowledgeId = NewType("KnowledgeId", str)
TenantId = NewType("TenantId", str)
AgentId = NewType("AgentId", str)
SessionId = NewType("SessionId", str)
RequestId = NewType("RequestId", str)
ProposalId = NewType("ProposalId", str)
ActorId = NewType("ActorId", str)
ChecksumSha256 = NewType("ChecksumSha256", str)
PolicyVersion = NewType("PolicyVersion", str)

KnowledgeIdValue = Annotated[
    str,
    BeforeValidator(_normalize_non_empty),
    StringConstraints(min_length=1, max_length=255),
]
TenantIdValue = Annotated[
    str,
    BeforeValidator(_normalize_non_empty),
    StringConstraints(min_length=1, max_length=128),
]
RequestIdValue = Annotated[
    str,
    BeforeValidator(_normalize_non_empty),
    StringConstraints(min_length=1, max_length=255),
]
ActorIdValue = Annotated[
    str,
    BeforeValidator(_normalize_non_empty),
    StringConstraints(min_length=1, max_length=255),
]
ChecksumSha256Value = Annotated[
    str,
    BeforeValidator(_validate_sha256),
    StringConstraints(pattern=r"^[0-9a-f]{64}$"),
]
DataClassificationValue = Annotated[
    str,
    AfterValidator(_validate_data_classification),
]


def make_knowledge_id(value: str) -> KnowledgeId:
    return KnowledgeId(_normalize_non_empty(value))


def make_tenant_id(value: str) -> TenantId:
    return TenantId(_normalize_non_empty(value))


def make_request_id(value: str) -> RequestId:
    return RequestId(_normalize_non_empty(value))


def make_actor_id(value: str) -> ActorId:
    return ActorId(_normalize_non_empty(value))


def make_checksum_sha256(value: str) -> ChecksumSha256:
    return ChecksumSha256(_validate_sha256(value))

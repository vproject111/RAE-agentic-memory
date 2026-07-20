from __future__ import annotations

import hashlib
import json
from typing import Any

from rae_core.models.evidence import EvidenceBundle
from rae_core.types.branded import ChecksumSha256, make_checksum_sha256


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _safe_round(val: Any) -> float:
    try:
        import math
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return 0.0
        return round(f_val, 6)
    except (ValueError, TypeError):
        return 0.0


def calculate_content_hash(bundle: EvidenceBundle) -> ChecksumSha256:
    evidence = [
        {
            "knowledge_id": item.knowledge_id,
            "source_ref": item.source_ref,
            "source_type": item.source_type.value,
            "authority_level": item.authority_level.value,
            "relevance": _safe_round(item.relevance),
            "freshness": _safe_round(item.freshness),
            "scope_match": _safe_round(item.scope_match),
            "checksum": item.checksum,
            "observed_at": item.observed_at.isoformat(),
            "supports": sorted(item.supports),
            "contradicts": sorted(item.contradicts),
        }
        for item in bundle.evidence
    ]

    conflicts = [
        {
            "subject": conflict.subject,
            "source_a": conflict.source_a,
            "source_b": conflict.source_b,
            "conflict_type": conflict.conflict_type.value,
            "severity": conflict.severity.value,
            "preferred_source": conflict.preferred_source,
            "resolution_rule": conflict.resolution_rule,
        }
        for conflict in bundle.conflicts
    ]

    payload = {
        "tenant_id": bundle.tenant_id,
        "query": bundle.query,
        "policy_version": bundle.policy_version,
        "evidence": sorted(
            evidence,
            key=lambda item: (
                item["source_ref"],
                item["checksum"],
            ),
        ),
        "conflicts": sorted(
            conflicts,
            key=lambda item: (
                item["subject"],
                item["source_a"],
                item["source_b"],
            ),
        ),
        "unresolved_questions": sorted(bundle.unresolved_questions),
        "confidence": _safe_round(bundle.confidence),
        "resolution_status": bundle.resolution_status.value,
    }

    return make_checksum_sha256(
        hashlib.sha256(_canonical_json(payload)).hexdigest()
    )


def calculate_audit_hash(
    bundle: EvidenceBundle,
    *,
    previous_audit_hash: str | None,
) -> ChecksumSha256:
    payload = {
        "bundle_id": str(bundle.bundle_id),
        "tenant_id": bundle.tenant_id,
        "request_id": bundle.request_id,
        "generated_at": bundle.generated_at.isoformat(),
        "content_hash": bundle.content_hash,
        "previous_audit_hash": previous_audit_hash,
    }
    return make_checksum_sha256(
        hashlib.sha256(_canonical_json(payload)).hexdigest()
    )

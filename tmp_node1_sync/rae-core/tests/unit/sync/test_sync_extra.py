from datetime import datetime, timedelta

from cryptography.fernet import Fernet

from rae_core.sync.encryption import E2EEncryption
from rae_core.sync.merge import ConflictResolutionStrategy, ConflictResolver


def test_sync_encryption_init_with_key():
    key = Fernet.generate_key()
    enc = E2EEncryption(key=key)
    assert enc.key == key


def test_conflict_resolver_fields_strategy():
    resolver = ConflictResolver()
    now = datetime.now()
    past = now - timedelta(days=1)

    local = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "content": "local",
        "tags": ["t1"],
        "modified_at": now,
    }
    remote = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "content": "remote",
        "tags": ["t2"],
        "modified_at": past,
    }

    # Line 72
    res = resolver.resolve(
        local,
        remote,
        conflict_fields=["tags"],
        strategy=ConflictResolutionStrategy.MERGE_FIELDS,
    )
    assert res.success
    assert res.merged_memory is not None
    assert res.merged_memory["content"] == "local"

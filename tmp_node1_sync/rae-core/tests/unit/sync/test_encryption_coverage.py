"""Unit tests for encryption.py to achieve 100% coverage."""

from typing import Any, cast

from rae_core.sync.encryption import E2EEncryption, decrypt_batch, encrypt_batch


class TestEncryptionCoverage:
    """Test suite for encryption.py coverage gaps."""

    def test_init_with_password(self):
        """Test initialization with password derivation."""
        e1 = E2EEncryption(password="test-password")
        e2 = E2EEncryption(password="test-password")
        assert e1.key == e2.key

        e3 = E2EEncryption(password="different")
        assert e1.key != e3.key

    def test_init_default(self):
        """Test default initialization (generate new key)."""
        e = E2EEncryption()
        assert e.key is not None
        assert len(e.key) > 0

    def test_encrypt_decrypt_basic(self):
        """Test basic encryption and decryption of Any data."""
        e = E2EEncryption()
        data = {"secret": "value", "number": 42}
        encrypted = e.encrypt(data)
        decrypted = e.decrypt(encrypted)
        assert decrypted == data

    def test_encrypt_decrypt_memory(self):
        """Test memory record encryption/decryption."""
        e = E2EEncryption()
        memory = {
            "id": "123",
            "content": "top secret",
            "metadata": {"sensitive": True},
            "public": "visible",
        }

        enc = e.encrypt_memory(memory)
        assert enc["content"] != "top secret"
        assert enc["content_encrypted"] is True
        assert enc["metadata_encrypted"] is True
        assert enc["public"] == "visible"

        dec = e.decrypt_memory(enc)
        assert dec["content"] == "top secret"
        assert dec["metadata"] == {"sensitive": True}
        assert "content_encrypted" not in dec

    def test_batch_operations(self):
        """Test batch encryption and decryption."""
        e = E2EEncryption()
        mems = [{"content": "c1", "metadata": {}}, {"content": "c2"}]

        enc_mems = encrypt_batch(cast(list[dict[str, Any]], mems), e)
        assert len(enc_mems) == 2
        assert enc_mems[0]["content_encrypted"] is True

        dec_mems = decrypt_batch(enc_mems, e)
        assert dec_mems == mems

    def test_generate_key_static(self):
        """Test the static generate_key method."""
        key = E2EEncryption.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_get_key(self):
        """Test get_key method."""
        e = E2EEncryption()
        assert e.get_key() == e.key.decode()

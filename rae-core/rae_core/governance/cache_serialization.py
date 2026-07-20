from __future__ import annotations

import msgpack
import zstandard

CACHE_SCHEMA_VERSION = 3
COMPRESSION_THRESHOLD = 32 * 1024
MAX_DECOMPRESSED_BYTES = 4 * 1024 * 1024


class CacheDecodeError(ValueError):
    pass


def pack_cache_value(document: dict) -> bytes:
    raw = msgpack.packb(
        document,
        use_bin_type=True,
        strict_types=True,
    )

    if len(raw) >= COMPRESSION_THRESHOLD:
        compressed = zstandard.ZstdCompressor(level=3).compress(raw)
        envelope = {
            "v": CACHE_SCHEMA_VERSION,
            "c": "zstd",
            "n": len(raw),
            "p": compressed,
        }
    else:
        envelope = {
            "v": CACHE_SCHEMA_VERSION,
            "c": "none",
            "n": len(raw),
            "p": raw,
        }

    return msgpack.packb(envelope, use_bin_type=True, strict_types=True)


def unpack_cache_value(value: bytes) -> dict:
    envelope = msgpack.unpackb(
        value,
        raw=False,
        strict_map_key=True,
    )

    if envelope.get("v") != CACHE_SCHEMA_VERSION:
        raise CacheDecodeError("Nieobsługiwana wersja cache")

    expected_size = int(envelope["n"])
    if expected_size < 0 or expected_size > MAX_DECOMPRESSED_BYTES:
        raise CacheDecodeError("Niepoprawny rozmiar payloadu")

    payload = envelope["p"]
    if envelope["c"] == "zstd":
        raw = zstandard.ZstdDecompressor().decompress(
            payload,
            max_output_size=MAX_DECOMPRESSED_BYTES,
        )
    elif envelope["c"] == "none":
        raw = payload
    else:
        raise CacheDecodeError("Nieobsługiwana kompresja")

    if len(raw) != expected_size:
        raise CacheDecodeError("Niezgodny rozmiar payloadu")

    document = msgpack.unpackb(
        raw,
        raw=False,
        strict_map_key=True,
    )
    if not isinstance(document, dict):
        raise CacheDecodeError("Payload cache nie jest mapą")
    return document

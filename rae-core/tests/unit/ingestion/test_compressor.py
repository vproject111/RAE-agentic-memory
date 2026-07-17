from rae_core.ingestion.compressor import IngestChunk, IngestCompressor


def test_compress_skip_non_log_policy():
    compressor = IngestCompressor()
    chunks = [IngestChunk(content="test", metadata={}, offset=0, length=4)]

    result_chunks, provenance, audit = compressor.compress(chunks, "POLICY_PROSE_TEXT")

    assert result_chunks == chunks
    assert audit.action == "skip"


def test_compress_deduplication():
    compressor = IngestCompressor()
    chunks = [
        IngestChunk(
            content="2023-01-01 10:00:00 ERROR: Connection failed",
            metadata={},
            offset=0,
            length=42,
        ),
        IngestChunk(
            content="2023-01-01 10:00:01 ERROR: Connection failed",
            metadata={},
            offset=42,
            length=42,
        ),
        IngestChunk(
            content="2023-01-01 10:00:02 INFO: System ok",
            metadata={},
            offset=84,
            length=33,
        ),
    ]

    # The current implementation uses lines[0][:40] as pattern.
    # "2023-01-01 10:00:00 ERROR: Connection fa"
    # "2023-01-01 10:00:01 ERROR: Connection fa"
    # They are DIFFERENT because of seconds.
    # Wait, let's check the logic in compressor.py: pattern = lines[0][:40]

    # If I want them to be same, I should make them same in first 40 chars.
    chunks = [
        IngestChunk(
            content="ERROR: Connection failed at 10:00:00",
            metadata={},
            offset=0,
            length=36,
        ),
        IngestChunk(
            content="ERROR: Connection failed at 10:00:01",
            metadata={},
            offset=36,
            length=36,
        ),
        IngestChunk(content="INFO: System ok", metadata={}, offset=72, length=15),
    ]
    # "ERROR: Connection failed at 10:00:00" -> first 40 is the whole line.
    # Still different.

    # Let's use a pattern that IS the same.
    chunks = [
        IngestChunk(
            content="LOG_PREFIX: some unique data 1", metadata={}, offset=0, length=30
        ),
        IngestChunk(
            content="LOG_PREFIX: some unique data 2", metadata={}, offset=30, length=30
        ),
        IngestChunk(content="OTHER_PREFIX: data", metadata={}, offset=60, length=18),
    ]
    # "LOG_PREFIX: some unique data 1" [:40] is "LOG_PREFIX: some unique data 1"
    # Still different.

    # OK, let's make it EXACTLY same for first 40.
    chunks = [
        IngestChunk(
            content="SAME_PREFIX_FOR_THESE_TWO_CHUNKS_HERE_1234567890",
            metadata={},
            offset=0,
            length=48,
        ),
        IngestChunk(
            content="SAME_PREFIX_FOR_THESE_TWO_CHUNKS_HERE_1234567890_suffix",
            metadata={},
            offset=48,
            length=55,
        ),
    ]

    result_chunks, provenance, audit = compressor.compress(chunks, "POLICY_LOG_STREAM")

    assert len(result_chunks) == 1
    assert audit.action == "deduplication"
    assert provenance[0] == [0, 1]


def test_compress_empty_chunks():
    compressor = IngestCompressor()
    result_chunks, provenance, audit = compressor.compress([], "POLICY_LOG_STREAM")
    assert len(result_chunks) == 0
    assert audit.trace["ratio"] == 1.0

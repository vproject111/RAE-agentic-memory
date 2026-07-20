import pytest

from rae_core.ingestion.segmenter import ContentSignature, IngestSegmenter


@pytest.mark.asyncio
async def test_segment_log_stream():
    config = {
        "ingest_params": {"boundary_patterns": {"log_timestamp": r"^\d{4}-\d{2}-\d{2}"}}
    }
    segmenter = IngestSegmenter(config)
    text = "2023-01-01 Line 1\n2023-01-02 Line 2\n  Continuation of Line 2"
    sig = ContentSignature(struct={}, dist={}, stab={})

    chunks, audit = await segmenter.segment(text, "POLICY_LOG_STREAM", sig)

    assert len(chunks) == 1
    assert "2023-01-01 Line 1" in chunks[0].content
    assert "2023-01-02 Line 2\n  Continuation of Line 2" in chunks[0].content


@pytest.mark.asyncio
async def test_segment_procedure_doc():
    config = {"ingest_params": {"boundary_patterns": {"procedure_step": r"^Step \d+:"}}}
    segmenter = IngestSegmenter(config)
    text = "Step 1: Open door\nStep 2: Close door"
    sig = ContentSignature(struct={}, dist={}, stab={})

    chunks, audit = await segmenter.segment(text, "POLICY_PROCEDURE_DOC", sig)

    assert len(chunks) == 1
    assert "Step 1: Open door" in chunks[0].content
    assert "Step 2: Close door" in chunks[0].content


@pytest.mark.asyncio
async def test_afe_extraction():
    config = {
        "ingest_params": {
            "extraction_rules": {
                "error_code": {"pattern": r"ERROR_(\d+)", "mapping": {"1": "code"}}
            }
        }
    }
    segmenter = IngestSegmenter(config)
    text = "System failed with ERROR_500"
    sig = ContentSignature(struct={}, dist={}, stab={})

    chunks, audit = await segmenter.segment(text, "POLICY_DEFAULT", sig)

    assert chunks[0].metadata["extracted_features"]["code"] == 500


@pytest.mark.asyncio
async def test_aggregate_atoms_oversized():
    config = {"ingest_params": {"target_chunk_size": 10, "hard_limit": 20}}
    segmenter = IngestSegmenter(config)
    # Oversized atom: 36 chars
    text = "ThisIsAVeryLongAtomThatExceedsLimits"
    sig = ContentSignature(struct={}, dist={}, stab={})

    chunks, audit = await segmenter.segment(text, "POLICY_DEFAULT", sig)

    assert len(chunks) == 4
    for c in chunks:
        assert c.metadata["oversized_atom"] is True


@pytest.mark.asyncio
async def test_segment_default_paragraphs():
    segmenter = IngestSegmenter()
    text = "Para 1\n\nPara 2"
    sig = ContentSignature(struct={}, dist={}, stab={})
    chunks, audit = await segmenter.segment(text, "POLICY_DEFAULT", sig)
    assert len(chunks) == 1

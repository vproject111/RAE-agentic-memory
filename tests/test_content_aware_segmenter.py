"""
Integration test for Atomic Segmenter (System 40.6).
Verifies that logical atoms (log entries, steps) stay together under size pressure.
"""

import pytest
from rae_core.ingestion.segmenter import IngestSegmenter
from rae_core.ingestion.interfaces import ContentSignature

@pytest.mark.asyncio
async def test_atomic_log_segmentation_stays_together():
    # Setup config with VERY SMALL soft limit to force pressure
    config = {
        "ingest_params": {
            "target_chunk_size": 20, 
            "hard_limit": 1000, # Allow entries to grow
            "boundary_patterns": {
                "log_timestamp": r'^\[\d{2}:\d{2}\]' 
            }
        }
    }
    
    segmenter = IngestSegmenter(config=config)
    
    # Text with a multi-line entry that is much bigger than target_chunk_size (20)
    text = (
        "[10:00] Entry 1\n"
        "[10:05] Entry 2 with a very long body that spans multiple lines\n"
        "and contains a lot of technical details that must not be split.\n"
        "This whole block belongs to [10:05].\n"
        "[10:10] Entry 3"
    )
    
    sig = ContentSignature(struct={"mode": "LINEAR_LOG_LIKE"}, dist={}, stab={})
    chunks, _ = await segmenter.segment(text, "POLICY_LOG_STREAM", sig)
    
    # Validation
    # We expect Entry 2 to be in its own chunk, and NOT split, 
    # even though it's much larger than 20 chars.
    entry_2_chunk = next(c for c in chunks if "Entry 2" in c.content)
    
    print(f"\nChunk containing Entry 2 (Size {len(entry_2_chunk.content)}):")
    print(entry_2_chunk.content)
    
    assert "belongs to [10:05]" in entry_2_chunk.content
    assert "[10:10]" not in entry_2_chunk.content # Entry 3 is in the NEXT chunk
    assert len(chunks) == 3

@pytest.mark.asyncio
async def test_procedural_steps_stay_atomic():
    config = {
        "ingest_params": {
            "target_chunk_size": 10, # Aggressive pressure
            "hard_limit": 500,
            "boundary_patterns": {
                "procedure_step": r'^Step \d+:'
            }
        }
    }
    segmenter = IngestSegmenter(config=config)
    
    text = (
        "Step 1: Open the valve slowly.\n"
        "Step 2: Check pressure gauge.\n"
        "Step 3: Log the result."
    )
    
    sig = ContentSignature(struct={"mode": "LIST_PROCEDURE_LIKE"}, dist={}, stab={})
    chunks, _ = await segmenter.segment(text, "POLICY_PROCEDURE_DOC", sig)
    
    # Each step should be its own chunk because each step > 10 chars
    # and we don't split atoms.
    assert len(chunks) == 3
    assert chunks[0].content == "Step 1: Open the valve slowly."
    assert chunks[1].content == "Step 2: Check pressure gauge."

if __name__ == "__main__":
    pytest.main([__file__])

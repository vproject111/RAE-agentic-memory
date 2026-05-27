"""
Integration test for Automatic Feature Extraction (System 40.7).
Verifies that machine metrics (Speed, Job ID) are captured during ingestion.
"""

import pytest
from rae_core.ingestion.segmenter import IngestSegmenter
from rae_core.ingestion.interfaces import ContentSignature

@pytest.mark.asyncio
async def test_truejet_feature_extraction():
    config = {
        "ingest_params": {
            "target_chunk_size": 1000,
            "boundary_patterns": {
                "log_timestamp": r'^\[\d{2}:\d{2}\]' 
            },
            "extraction_rules": {
                "truejet_speed": {
                    "pattern": r'Speed:\s*(\d+\.?\d*)m\?\((\d+\.?\d*)m\)/h',
                    "mapping": {1: "speed_m2h", 2: "speed_mh"}
                },
                "truejet_size": {
                    "pattern": r'Size:\s*(\d+)x',
                    "mapping": {1: "width_mm"}
                },
                "generic_job_id": {
                    "pattern": r'Job\s*ID:\s*([A-Z0-9-]+)',
                    "mapping": {1: "job_id"}
                }
            }
        }
    }
    
    segmenter = IngestSegmenter(config=config)
    
    # Text simulating a machine log entry for TrueJet2
    text = (
        "[12:00] Machine Status: RUNNING\n"
        "Job ID: TX-998877-A\n"
        "Size: 1600x2000mm\n"
        "Speed: 120.5m?(80.3m)/h\n"
        "Ink: 45ml"
    )
    
    sig = ContentSignature(struct={"mode": "LINEAR_LOG_LIKE"}, dist={}, stab={})
    chunks, audit = await segmenter.segment(text, "POLICY_LOG_STREAM", sig)
    
    assert len(chunks) == 1
    extracted = chunks[0].metadata.get("extracted_features", {})
    
    print("\nExtracted Features:")
    print(extracted)
    
    assert extracted.get("speed_m2h") == 120.5
    assert extracted.get("speed_mh") == 80.3
    assert extracted.get("width_mm") == 1600
    assert extracted.get("job_id") == "TX-998877-A"
    
    assert "atomic_splitting_with_afe" in audit.action

if __name__ == "__main__":
    pytest.main([__file__])

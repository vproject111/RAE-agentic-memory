from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rae_core.ingestion.interfaces import ContentSignature
from rae_core.ingestion.semantic_segmenter import SemanticRecursiveSegmenter


class TestSemanticSegmenter:
    @pytest.fixture
    def segmenter(self):
        config = {"ingest_params": {"target_chunk_size": 100, "hard_limit": 300}}
        with (
            patch("rae_core.embedding.native.Tokenizer"),
            patch("rae_core.embedding.native.ort.InferenceSession"),
        ):
            return SemanticRecursiveSegmenter(chunk_size=100)

    @pytest.mark.asyncio
    async def test_segment_basic(self, segmenter):
        text = "This is a sentence. This is another sentence that is quite long and should be preserved."
        signature = ContentSignature(
            struct={"data_type": "text", "language": "en"}, dist={}, stab={}
        )

        segmenter._embedder = MagicMock()
        segmenter._embedder.embed_batch = AsyncMock(return_value=[[0.1] * 384])

        chunks, audit = await segmenter.segment(text, signature=signature)

        assert len(chunks) > 0
        assert audit.stage == "segment"

    @pytest.mark.asyncio
    async def test_segment_empty_text(self, segmenter):
        text = ""
        signature = ContentSignature(struct={}, dist={}, stab={})
        chunks, audit = await segmenter.segment(text, signature=signature)
        # Empty text should return empty chunks or single empty chunk depending on logic
        # Current logic returns [] if text.strip() is empty
        assert len(chunks) == 0

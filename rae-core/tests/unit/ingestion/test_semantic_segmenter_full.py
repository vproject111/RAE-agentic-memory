from unittest.mock import AsyncMock, patch

import pytest

from rae_core.ingestion.interfaces import ContentSignature
from rae_core.ingestion.semantic_segmenter import (
    SemanticRecursiveSegmenter,
)


class TestSemanticSegmenterFull:
    @pytest.fixture
    def mock_embedder(self):
        with patch(
            "rae_core.ingestion.semantic_segmenter.NativeEmbeddingProvider"
        ) as mock:
            mock_inst = mock.return_value
            mock_inst.embed_batch = AsyncMock(
                return_value=[[0.1] * 384, [0.1] * 384, [0.1] * 384]
            )
            yield mock

    def test_init_defaults(self, mock_embedder):
        segmenter = SemanticRecursiveSegmenter()
        assert segmenter._chunk_size == 1000

    @pytest.mark.asyncio
    async def test_semantic_split_empty(self, mock_embedder):
        segmenter = SemanticRecursiveSegmenter()
        assert await segmenter._semantic_split("") == []

    @pytest.mark.asyncio
    async def test_semantic_split_thresholding(self, mock_embedder):
        segmenter = SemanticRecursiveSegmenter(semantic_threshold_percentile=50)
        mock_inst = mock_embedder.return_value
        # We provide 3 embeddings -> 2 similarities
        mock_inst.embed_batch.return_value = [
            [1.0, 0.0],  # s1
            [0.9, 0.0],  # s2 (similar to s1)
            [0.0, 1.0],  # s3 (different from s2)
        ]
        text = "Sentence one. Sentence two. Sentence three."
        chunks = await segmenter._semantic_split(text)
        assert len(chunks) == 2

    def test_perform_structural_split_no_separator_match(self, mock_embedder):
        segmenter = SemanticRecursiveSegmenter(chunk_size=10)
        text = "0123456789ABCDE"
        chunks = segmenter._perform_structural_split(text, [" ", ""])
        assert len(chunks) == 2
        assert chunks[0] == "0123456789"
        assert chunks[1] == "ABCDE"

    @pytest.mark.asyncio
    async def test_segment_integration(self, mock_embedder):
        segmenter = SemanticRecursiveSegmenter(chunk_size=50)
        mock_inst = mock_embedder.return_value
        mock_inst.embed_batch.return_value = [[0.1] * 384] * 10

        text = "Part 1. Part 2. Part 3. Part 4. Part 5. Part 6. Part 7. Part 8."
        signature = ContentSignature(struct={"type": "test"}, dist={}, stab={})

        chunks, audit = await segmenter.segment(
            text, policy="custom_policy", signature=signature
        )
        assert len(chunks) > 0

    def test_perform_structural_split_empty_parts(self, mock_embedder):
        segmenter = SemanticRecursiveSegmenter(chunk_size=100)
        text = "Part 1\n\n\n\nPart 2"
        chunks = segmenter._perform_structural_split(text, ["\n\n"])
        # Aggregation joins with \n\n, so empty parts are filtered by .strip()
        assert len(chunks) == 1
        assert "Part 1" in chunks[0]
        assert "Part 2" in chunks[0]

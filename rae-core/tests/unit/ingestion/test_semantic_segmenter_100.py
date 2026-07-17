from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from rae_core.ingestion.semantic_segmenter import (
    SemanticRecursiveSegmenter,
    _calculate_similarity_scores,
)


class TestSemanticSegmenter100:
    @pytest.fixture
    def segmenter(self):
        with (
            patch("rae_core.embedding.native.Tokenizer"),
            patch("rae_core.embedding.native.ort.InferenceSession"),
        ):
            s = SemanticRecursiveSegmenter(chunk_size=100)
            s._embedder = MagicMock()
            s._embedder.embed_batch = AsyncMock()
            return s

    def test_calculate_similarity_scores_empty(self):
        # Line 26: return [] if embeddings.shape[0] < 2
        assert _calculate_similarity_scores(np.array([])) == []
        assert _calculate_similarity_scores(np.array([[0.1, 0.2]])) == []

    @pytest.mark.asyncio
    async def test_semantic_split_single_sentence(self, segmenter):
        # Line 79-80: return [text] if len(processed_sentences) <= 1
        text = "Just one sentence."
        # With default separators ['. ', '? ', '! ', '\n'], this text might result in one processed sentence
        # but re.split might return ['', 'Just one sentence.']?
        # Actually re.split(f"({'|'.join(map(re.escape, self._semantic_separators))})", text)
        # for "Just one sentence." will return ["Just one sentence."]
        result = await segmenter._semantic_split(text)
        assert result == [text]

    @pytest.mark.asyncio
    async def test_semantic_split_no_similarities(self, segmenter):
        # Line 97: return [text] if not similarities
        # This can happen if processed_sentences has 2 items but one is empty?
        # Actually if _calculate_similarity_scores returns []
        text = "Sentence one. Sentence two."
        segmenter._embedder.embed_batch.return_value = [[0.1] * 384, [0.1] * 384]

        with patch(
            "rae_core.ingestion.semantic_segmenter._calculate_similarity_scores",
            return_value=[],
        ):
            result = await segmenter._semantic_split(text)
            assert result == [text]

    @pytest.mark.asyncio
    async def test_segment_empty_structural_split(self, segmenter):
        # Lines 133-134: if split.strip(): final_chunks.append(split)
        # We need _perform_structural_split to return a list containing an empty string or whitespace string
        with patch.object(
            segmenter, "_perform_structural_split", return_value=["   ", "valid chunk"]
        ):
            chunks, audit = await segmenter.segment("some text")
            assert len(chunks) == 1
            assert chunks[0].content == "valid chunk"

    @pytest.mark.asyncio
    async def test_perform_structural_split_no_separator(self, segmenter):
        # Line 174: return [text] if separator is None
        # This happens if none of the separators are in the text AND len(text) > chunk_size
        segmenter._chunk_size = 5
        text = "abcdefgh"  # length 8 > 5
        # separators are ["\n\n", "\n", " ", ""]
        # Wait, "" is always at the end of separators.
        # If we provide custom separators without ""
        segmenter._structural_separators = ["X", "Y"]
        result = segmenter._perform_structural_split(
            text, segmenter._structural_separators
        )
        assert result == [text]

    @pytest.mark.asyncio
    async def test_perform_structural_split_empty_part(self, segmenter):
        # Line 187: if not part.strip(): continue
        # Happens if text has consecutive separators
        segmenter._chunk_size = 2  # Small chunk size to force splitting
        # "a\n\nb" length 4 > 2.
        # separators ["\n"]
        # splits = ["a", "", "b"]
        # part="a", aggregated=["a"], length=1
        # part="", skip (LINE 187)
        # part="b", length 1 + 1 + 1 = 3 > 2.
        # So it will append aggregated "a" to structural_chunks.
        # then recurse on "b" with separators[1:] which is []
        # _perform_structural_split("b", []) returns ["b"]
        # final result ["a", "b"]
        result = segmenter._perform_structural_split("a\n\nb", ["\n"])
        assert result == ["a", "b"]

    @pytest.mark.asyncio
    async def test_semantic_split_empty_or_single(self, segmenter):
        # Line 86: return [text] if len(processed_sentences) <= 1
        assert await segmenter._semantic_split("   ") == []
        assert await segmenter._semantic_split("Just one sentence.") == [
            "Just one sentence."
        ]

    @pytest.mark.asyncio
    async def test_semantic_split_with_delimiter(self, segmenter):
        # Line 79-80: delimiter and i += 1
        text = "Sentence one.Sentence two."
        # This should have "." as delimiter
        segmenter._semantic_separators = ["."]
        # re.split will return ["Sentence one", ".", "Sentence two."]
        # sentences[1].strip() will be "." which is in self._semantic_separators
        segmenter._embedder.embed_batch.return_value = [[0.1] * 384, [0.2] * 384]
        result = await segmenter._semantic_split(text)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_segment_large_split(self, segmenter):
        # Lines 133-134: semantic_split call and extend
        segmenter._chunk_size = 5
        # We want _perform_structural_split to return a split > 5
        with patch.object(
            segmenter, "_perform_structural_split", return_value=["very long split"]
        ):
            segmenter._embedder.embed_batch.return_value = [[0.1] * 384]
            chunks, audit = await segmenter.segment("anything")
            assert len(chunks) > 0

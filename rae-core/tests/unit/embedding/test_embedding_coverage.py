from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from rae_core.embedding.native import NativeEmbeddingProvider
from rae_core.embedding.onnx_cross_encoder import OnnxCrossEncoder


class TestEmbeddingCoverage:
    @pytest.fixture
    def mock_onnx(self):
        with (
            patch("rae_core.embedding.native.ort.InferenceSession") as mock_sess,
            patch("rae_core.embedding.native.Tokenizer") as mock_tok,
        ):
            # Mock session run return value: (batch, seq, dim)
            mock_sess.return_value.run.return_value = [np.array([[[0.1] * 384]])]
            # Mock session inputs
            mock_sess.return_value.get_inputs.return_value = [
                MagicMock(name="input_ids")
            ]
            mock_sess.return_value.get_outputs.return_value = [
                MagicMock(name="last_hidden_state")
            ]

            # Mock tokenizer encode return value
            mock_enc = MagicMock()
            mock_enc.ids = [1]
            mock_enc.attention_mask = [1]
            mock_tok.from_file.return_value.encode.return_value = mock_enc
            # Batch mode returns list of encodings
            mock_tok.from_file.return_value.encode_batch.return_value = [mock_enc]
            yield mock_sess, mock_tok

    @pytest.mark.asyncio
    async def test_native_provider_embed_batch(self, mock_onnx):
        provider = NativeEmbeddingProvider(model_path="m.onnx", tokenizer_path="t.json")
        embeddings = await provider.embed_batch(["text1"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 384

    @pytest.mark.asyncio
    async def test_native_provider_error_handling(self, mock_onnx):
        mock_sess, _ = mock_onnx
        mock_sess.return_value.run.side_effect = Exception("Inference error")
        with pytest.raises(
            RuntimeError, match="Failed to inspect ONNX model dimension"
        ):
            NativeEmbeddingProvider(model_path="m.onnx", tokenizer_path="t.json")

    @pytest.mark.asyncio
    async def test_cross_encoder_rerank(self):
        with (
            patch(
                "rae_core.embedding.onnx_cross_encoder.ort.InferenceSession"
            ) as mock_sess,
            patch("rae_core.embedding.onnx_cross_encoder.Tokenizer") as mock_tok,
        ):
            mock_sess.return_value.run.return_value = [np.array([[0.9], [0.1]])]
            mock_sess.return_value.get_inputs.return_value = []

            encoder = OnnxCrossEncoder(model_path="m.onnx", tokenizer_path="t.json")
            scores = encoder.predict([("q", "d1"), ("q", "d2")])
            assert scores[0] > scores[1]
            assert len(scores) == 2

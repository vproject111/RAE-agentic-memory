from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from rae_core.embedding.native import NativeEmbeddingProvider

# We need to be careful with imports since NativeEmbeddingProvider imports onnxruntime at top level
# If it's already imported, we might need to reload it or patch the module it's in.


class TestNativeEmbeddingProviderCoverage:
    def test_import_error(self):
        with patch("rae_core.embedding.native.ort", None):
            with pytest.raises(
                ImportError, match="onnxruntime and tokenizers are required"
            ):
                NativeEmbeddingProvider("m", "t")

    @patch("onnxruntime.InferenceSession")
    @patch("tokenizers.Tokenizer.from_file")
    def test_gpu_logic_and_dimension(self, mock_tokenizer, mock_session):
        # Setup mocks
        mock_tokenizer.return_value = MagicMock()
        session_instance = MagicMock()
        mock_session.return_value = session_instance

        # Mock inputs/outputs for dimension inspection
        input_mock = MagicMock()
        input_mock.name = "input_ids"
        session_instance.get_inputs.return_value = [input_mock]

        output_mock = MagicMock()
        output_mock.name = "output"
        session_instance.get_outputs.return_value = [output_mock]

        # Mock run for dimension inspection
        session_instance.run.return_value = [np.zeros((1, 1, 768))]

        with patch(
            "onnxruntime.get_available_providers",
            return_value=["CUDAExecutionProvider", "CPUExecutionProvider"],
        ):
            provider = NativeEmbeddingProvider(
                "model.onnx", "tokenizer.json", use_gpu=True
            )
            assert provider.get_dimension() == 768
            # Verify CUDA was attempted
            assert mock_session.call_count >= 1

    @patch("onnxruntime.InferenceSession")
    @patch("tokenizers.Tokenizer.from_file")
    def test_runtime_error_on_init(self, mock_tokenizer, mock_session):
        mock_tokenizer.return_value = MagicMock()
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        session_instance.run.side_effect = Exception("Inference failed")

        with pytest.raises(
            RuntimeError, match="Failed to inspect ONNX model dimension"
        ):
            NativeEmbeddingProvider("m", "t")

    @pytest.mark.asyncio
    @patch("onnxruntime.InferenceSession")
    @patch("tokenizers.Tokenizer.from_file")
    async def test_embed_batch_prefixes(self, mock_tokenizer, mock_session):
        mock_tokenizer.return_value = MagicMock()
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        session_instance.run.return_value = [np.zeros((2, 1, 768))]

        # Mock inputs
        input1 = MagicMock()
        input1.name = "input_ids"
        input2 = MagicMock()
        input2.name = "attention_mask"
        session_instance.get_inputs.return_value = [input1, input2]
        session_instance.get_outputs.return_value = [MagicMock()]

        provider = NativeEmbeddingProvider("m", "t", model_name="nomic-embed-text-v1.5")

        # Mock tokenizer encode_batch
        encoded = MagicMock()
        encoded.ids = [1, 2, 3]
        encoded.attention_mask = [1, 1, 1]
        mock_tokenizer.return_value.encode_batch.return_value = [encoded, encoded]

        # Test prefixes
        texts = ["hello", "search_query: already has prefix"]
        await provider.embed_batch(texts, task_type="search_query")

        # Verify tokenizer was called with prefixed "hello"
        call_args = mock_tokenizer.return_value.encode_batch.call_args[0][0]
        assert call_args[0] == "search_query: hello"
        assert call_args[1] == "search_query: already has prefix"

    @pytest.mark.asyncio
    @patch("onnxruntime.InferenceSession")
    @patch("tokenizers.Tokenizer.from_file")
    async def test_embed_batch_token_type_ids(self, mock_tokenizer, mock_session):
        mock_tokenizer.return_value = MagicMock()
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        session_instance.run.return_value = [np.zeros((1, 1, 768))]

        # Mock inputs with token_type_ids
        input_ids = MagicMock()
        input_ids.name = "input_ids"
        attention_mask = MagicMock()
        attention_mask.name = "attention_mask"
        token_type_ids = MagicMock()
        token_type_ids.name = "token_type_ids"
        session_instance.get_inputs.return_value = [
            input_ids,
            attention_mask,
            token_type_ids,
        ]
        session_instance.get_outputs.return_value = [MagicMock()]

        provider = NativeEmbeddingProvider("m", "t")

        encoded = MagicMock()
        encoded.ids = [1]
        encoded.attention_mask = [1]
        encoded.type_ids = [0]
        mock_tokenizer.return_value.encode_batch.return_value = [encoded]

        await provider.embed_batch(["test"])

        # Verify inputs to run
        run_args = session_instance.run.call_args[0][1]
        assert "token_type_ids" in run_args

    @pytest.mark.asyncio
    @patch("onnxruntime.InferenceSession")
    @patch("tokenizers.Tokenizer.from_file")
    async def test_embed_text(self, mock_tokenizer, mock_session):
        mock_tokenizer.return_value = MagicMock()
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        session_instance.run.return_value = [np.zeros((1, 1, 768))]
        session_instance.get_inputs.return_value = [MagicMock(), MagicMock()]
        session_instance.get_outputs.return_value = [MagicMock()]

        encoded = MagicMock()
        encoded.ids = [1]
        encoded.attention_mask = [1]
        mock_tokenizer.return_value.encode_batch.return_value = [encoded]

        provider = NativeEmbeddingProvider("m", "t")
        res = await provider.embed_text("hello")
        assert len(res) == 768

    @patch("onnxruntime.InferenceSession")
    @patch("tokenizers.Tokenizer.from_file")
    def test_gpu_failure(self, mock_tokenizer, mock_session):
        mock_tokenizer.return_value = MagicMock()

        def mock_init(path, providers=None):
            if providers and "CUDAExecutionProvider" in providers:
                raise Exception("CUDA failed")
            return MagicMock()

        mock_session.side_effect = mock_init

        with patch(
            "onnxruntime.get_available_providers",
            return_value=["CUDAExecutionProvider"],
        ):
            provider = NativeEmbeddingProvider("m", "t", use_gpu=True)
            # Should have fallen back to CPU
            assert mock_session.call_count >= 1

    def test_import_error_global(self):
        import importlib

        import rae_core.embedding.native

        # Patch builtins.__import__ to raise ImportError for onnxruntime
        real_import = __import__

        def mock_import(name, *args, **kwargs):
            if name in ("onnxruntime", "tokenizers"):
                raise ImportError(f"Mocked {name} error")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            importlib.reload(rae_core.embedding.native)
            assert rae_core.embedding.native.ort is None
            assert rae_core.embedding.native.Tokenizer is None

        # Reload back to normal
        importlib.reload(rae_core.embedding.native)
        assert rae_core.embedding.native.ort is not None

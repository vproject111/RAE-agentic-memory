import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from rae_lite.llm_adapter import LlamaCppAdapter

class TestLlamaCppAdapter:

    @pytest.fixture
    def mock_paths(self):
        return Path("/bin/llama-cli"), Path("/models/model.gguf")

    def test_init_available(self, mock_paths):
        """Adapter should be available if binary and model exist."""
        llama, model = mock_paths
        with patch.object(Path, "exists", return_value=True):
            adapter = LlamaCppAdapter(llama, model, profile="B")
            assert adapter.is_available is True

    def test_init_unavailable(self, mock_paths):
        """Adapter should be unavailable if binary missing."""
        llama, model = mock_paths
        with patch.object(Path, "exists", side_effect=[False, True]): # llama missing
            adapter = LlamaCppAdapter(llama, model, profile="B")
            assert adapter.is_available is False

    def test_generate_command_construction(self, mock_paths):
        """Verify CLI command construction."""
        llama, model = mock_paths
        with patch.object(Path, "exists", return_value=True):
            adapter = LlamaCppAdapter(llama, model, profile="D")
            
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "Response"
                
                adapter.generate("Test prompt")
                
                args = mock_run.call_args[0][0]
                assert str(llama) in args
                assert str(model) in args
                assert "-ngl" in args # Profile D enables GPU offload
                assert "99" in args

    def test_normalize_query_fallback(self, mock_paths):
        """Should return original query if profile is A."""
        llama, model = mock_paths
        adapter = LlamaCppAdapter(llama, model, profile="A")
        # Even if available, Profile A disables LLM
        query = "Show me memories about Python"
        assert adapter.normalize_query(query) == query

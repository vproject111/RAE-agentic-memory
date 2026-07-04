import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Import the module to test (we might need to import it by path if it's a script)
import importlib.util
spec = importlib.util.spec_from_file_location("bootstrap_session", "scripts/bootstrap_session.py")
bootstrap_session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap_session)

def test_check_service_success():
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        result = bootstrap_session.check_service("test", "http://test")
        assert result["status"] == "OK"
        assert result["details"] == {"status": "ok"}

def test_check_service_fallback():
    with patch('requests.get') as mock_get:
        # First call fails (ConnectionError)
        # Second call (fallback) succeeds
        
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {"status": "ok_fallback"}
        
        def side_effect(url, timeout):
            if "localhost" in url:
                return mock_response_ok
            raise Exception("Connection failed")
            
        mock_get.side_effect = side_effect
        
        result = bootstrap_session.check_service("test", "http://remote:8000")
        assert result["status"] == "OK"
        assert result["note"] == "Fallback to localhost"
        assert "localhost" in result["url"]

def test_check_service_failure():
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("All dead")
        
        result = bootstrap_session.check_service("test", "http://test")
        assert result["status"] == "OFFLINE"

def test_check_gemini_config():
    # Basic smoke test for the function
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{"env": {"RAE_API_URL": "http://localhost:8001"}}'
        # Should not print warning
        bootstrap_session.check_gemini_config("http://localhost:8001")

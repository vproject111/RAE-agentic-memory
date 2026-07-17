from unittest.mock import mock_open, patch

from rae_core.utils.contract_manager import ContractManager


def test_contract_manager_init_no_path():
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = False
        cm = ContractManager(contracts_path="/non/existent")
        assert cm.contracts_path == "/non/existent"
        assert cm.rules == {}


def test_contract_manager_load_contracts():
    with (
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
        patch("builtins.open", mock_open(read_data="binary_content")) as mock_file,
    ):

        mock_exists.return_value = True
        mock_listdir.return_value = ["rule1.bin", "not_a_rule.txt"]

        cm = ContractManager(contracts_path="/fake/path")

        assert "rule1.bin" in cm.rules
        assert cm.rules["rule1.bin"] == "binary_content"
        assert "not_a_rule.txt" not in cm.rules
        mock_file.assert_called_once_with("/fake/path/rule1.bin")


def test_verify_operation_valid():
    cm = ContractManager(contracts_path="/fake/path")
    success, message = cm.verify_operation("test_op", "low", "internal")
    assert success is True
    assert message == "OK"


def test_verify_operation_invalid():
    cm = ContractManager(contracts_path="/fake/path")
    # if info_class in ["restricted", "critical"] and impact_level != "high":
    success, message = cm.verify_operation("test_op", "low", "restricted")
    assert success is False
    assert "CRITICAL DATA REQUIRE HIGH IMPACT AUDIT" in message

    success, message = cm.verify_operation("test_op", "medium", "critical")
    assert success is False
    assert "CRITICAL DATA REQUIRE HIGH IMPACT AUDIT" in message

    success, message = cm.verify_operation("test_op", "high", "critical")
    assert success is True
    assert message == "OK"


def test_get_bootstrap_summary():
    with (
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
        patch("builtins.open", mock_open(read_data="Rule content")) as mock_file,
    ):

        mock_exists.return_value = True
        mock_listdir.return_value = ["SECURITY.bin"]

        cm = ContractManager(contracts_path="/fake/path")
        summary = cm.get_bootstrap_summary()

        assert "--- MANDATORY HARD CONTRACTS LOADED ---" in summary
        assert "[SECURITY.bin]:" in summary
        assert "Rule content" in summary

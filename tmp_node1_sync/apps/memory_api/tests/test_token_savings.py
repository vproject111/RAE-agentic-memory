from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from apps.memory_api.models.token_savings import SavingsSummary, TokenSavingsEntry
from apps.memory_api.services.token_savings_service import TokenSavingsService


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_repo):
    return TokenSavingsService(mock_repo)


@pytest.mark.asyncio
async def test_track_savings_positive(service, mock_repo):
    # Mock cost calculation
    with patch(
        "apps.memory_api.services.token_savings_service.calculate_cost"
    ) as mock_calc:
        mock_calc.return_value = {"total_cost_usd": 0.001}

        await service.track_savings(
            tenant_id="t1",
            project_id="p1",
            model="gpt-4",
            predicted_tokens=1000,
            real_tokens=200,
            savings_type="cache",
        )

        # Verify repository call
        mock_repo.log_savings.assert_called_once()
        call_args = mock_repo.log_savings.call_args[0][0]
        assert isinstance(call_args, TokenSavingsEntry)
        assert call_args.saved_tokens == 800  # 1000 - 200
        assert call_args.estimated_cost_saved_usd == 0.001


@pytest.mark.asyncio
async def test_track_savings_negative(service, mock_repo):
    # Should not log if real >= predicted
    await service.track_savings(
        tenant_id="t1",
        project_id="p1",
        model="gpt-4",
        predicted_tokens=100,
        real_tokens=200,  # Worse than predicted
        savings_type="rag",
    )

    mock_repo.log_savings.assert_not_called()


@pytest.mark.asyncio
async def test_get_summary(service, mock_repo):
    expected_summary = SavingsSummary(
        total_saved_tokens=500,
        total_saved_usd=0.05,
        savings_by_type={"cache": 500},
        period_start=datetime.now(),
        period_end=datetime.now(),
    )
    mock_repo.get_savings_summary.return_value = expected_summary

    result = await service.get_summary("t1")
    assert result == expected_summary
    mock_repo.get_savings_summary.assert_called_once()

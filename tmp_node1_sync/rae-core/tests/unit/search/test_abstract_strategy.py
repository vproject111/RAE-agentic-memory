import pytest

from rae_core.search.strategies import SearchStrategy


class DummyStrategy(SearchStrategy):
    async def search(self, query, tenant_id, filters=None, limit=10):
        # Removed super() call to abstract method
        return []

    def get_strategy_name(self):
        return "dummy"

    def get_strategy_weight(self):
        return 0.5


@pytest.mark.asyncio
async def test_search_strategy_abstract_calls():
    strategy = DummyStrategy()
    await strategy.search("test", "tenant")
    assert strategy.get_strategy_name() == "dummy"
    assert strategy.get_strategy_weight() == 0.5

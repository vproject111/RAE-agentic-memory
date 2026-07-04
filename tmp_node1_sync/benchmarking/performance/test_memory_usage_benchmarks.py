import pytest


@pytest.mark.performance
def test_memory_allocation_list_creation(benchmark):
    """
    Benchmarks the time taken to allocate a large list, simulating memory usage.
    """
    list_size = 10**6

    def create_large_list():
        return [i for i in range(list_size)]

    result = benchmark(create_large_list)

    assert len(result) == list_size

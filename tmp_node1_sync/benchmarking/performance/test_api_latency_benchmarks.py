import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Dummy FastAPI app for simulation
app = FastAPI()


@app.get("/dummy_endpoint")
async def dummy_endpoint():
    return {"message": "Hello, World!"}


@pytest.mark.performance
def test_api_latency_dummy_endpoint(benchmark):
    """
    Measures the latency of a dummy API endpoint.
    """
    client = TestClient(app)

    # Benchmark the request to the dummy endpoint
    result = benchmark(client.get, "/dummy_endpoint")

    assert result.status_code == 200
    assert result.json() == {"message": "Hello, World!"}

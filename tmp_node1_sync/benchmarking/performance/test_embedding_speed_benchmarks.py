import time

import pytest


@pytest.mark.performance
def test_embedding_generation_speed(benchmark):
    """
    Benchmarks the speed of generating embeddings for a list of texts.
    This is a placeholder for actual embedding model inference.
    """
    texts = [
        "This is a test sentence for embedding.",
        "Another sentence to be embedded.",
        "A third short text.",
        "A slightly longer sentence to check performance variation.",
    ] * 10  # Simulate more data

    def generate_embeddings():
        # Simulate embedding model inference
        for text in texts:
            time.sleep(0.001)  # Simulate some work
        return [f"embedding_of_{text}" for text in texts]  # Dummy embeddings

    embeddings = benchmark(generate_embeddings)

    assert len(embeddings) == len(texts)
    assert all(e.startswith("embedding_of_") for e in embeddings)

def estimate_tokens(text: str) -> int:
    """
    Estimates the number of tokens in a given text using a simple approximation.
    This is a naive approach; a proper tokenizer would be more accurate.
    """
    # Naive estimation: count words and multiply by an average factor
    # A common rule of thumb is ~1.3 tokens per word for English text.
    if not text:
        return 0
    return int(len(text.split()) * 1.3)

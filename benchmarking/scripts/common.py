import hashlib
import random


class UniquenessGuard:
    """Ensures content uniqueness across benchmarks."""

    def __init__(self):
        self.seen = set()

    def ensure_unique(self, text: str, max_retries: int = 20) -> str:
        for _ in range(max_retries):
            h = hashlib.md5(text.encode("utf-8")).hexdigest()
            if h not in self.seen:
                self.seen.add(h)
                return text
            # Add jitter to resolve collision
            text += f" [UID-{random.randint(0, 99999999)}]"
        return text

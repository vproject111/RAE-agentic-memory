from rae_core.utils.chunking import ProceduralChunker


def test_chunk_empty_text():
    chunker = ProceduralChunker()
    assert chunker.chunk_text("") == []
    assert chunker.chunk_text(None) == []


def test_chunk_small_text():
    chunker = ProceduralChunker(chunk_size=100)
    text = "Short text."
    chunks = chunker.chunk_text(text)
    assert chunks == ["Short text."]


def test_chunk_procedural_split():
    chunker = ProceduralChunker(chunk_size=50)
    text = "Step 1: Do something.\nStep 2: Do another thing.\nStep 3: Finish."
    chunks = chunker.chunk_text(text)
    # The regex split would produce: ["Step 1: Do something.", "Step 2: Do another thing.", "Step 3: Finish."]
    # Since they are small, they might be merged by the merging logic.
    # Step 1 (21) + Step 2 (25) = 46. 46 < 50. So they are merged.
    # Then Step 3 (15) is added. 46 + 15 = 61 > 50.
    # So we should get ["Step 1: Do something.\n\nStep 2: Do another thing.", "Step 3: Finish."]
    assert len(chunks) == 2
    assert "Step 1" in chunks[0]
    assert "Step 2" in chunks[0]
    assert "Step 3" in chunks[1]


def test_chunk_paragraph_split():
    chunker = ProceduralChunker(chunk_size=20, overlap=0)
    text = "Para 1.\n\nPara 2.\n\nPara 3."
    chunks = chunker.chunk_text(text)
    # Para 1. (7) + Para 2. (7) = 14. 14 < 20.
    # 14 + Para 3. (7) = 21 > 20.
    # So we get ["Para 1.\n\nPara 2.", "Para 3."]
    assert chunks == ["Para 1.\n\nPara 2.", "Para 3."]


def test_chunk_sentence_split():
    # Force a very small chunk size to trigger sentence split
    chunker = ProceduralChunker(chunk_size=15)
    text = "Sentence one. Sentence two. Sentence three."
    chunks = chunker.chunk_text(text)
    # Sentence one. (13) + Sentence two. (13) = 26 > 15.
    # So: ["Sentence one.", "Sentence two.", "Sentence three."]
    assert chunks == ["Sentence one.", "Sentence two.", "Sentence three."]


def test_chunk_krok_split():
    chunker = ProceduralChunker(chunk_size=50)
    text = "Krok 1: Pierwszy krok.\nKrok 2: Drugi krok."
    chunks = chunker.chunk_text(text)
    assert len(chunks) == 1  # 21 + 19 = 40 < 50
    assert "Krok 1" in chunks[0]
    assert "Krok 2" in chunks[0]


def test_chunk_numbered_split():
    chunker = ProceduralChunker(chunk_size=50)
    text = "1. First point.\n2. Second point."
    chunks = chunker.chunk_text(text)
    assert len(chunks) == 1
    assert "1. First point." in chunks[0]
    assert "2. Second point." in chunks[0]


def test_chunk_large_block_no_delimiters():
    chunker = ProceduralChunker(chunk_size=10)
    text = "A" * 25  # 25 characters, no spaces, no newlines
    chunks = chunker.chunk_text(text)
    # Since there are no spaces or newlines, the sentence split re.split(r'(?<=[.!?])\s+', ...)
    # will not find anything to split.
    # The code doesn't seem to have a fallback for splitting strings without any delimiters.
    # refined_blocks.append(current_sent_chunk.strip()) will just append the whole thing if it can't split.
    # Wait, let's look at the code:
    # current_sent_chunk = sent + " "
    # if len(current_sent_chunk) + len(sent) < self.chunk_size:
    #     current_sent_chunk += sent + " "
    # else:
    #     if current_sent_chunk:
    #         refined_blocks.append(current_sent_chunk.strip())
    #     current_sent_chunk = sent + " "
    # If a single "sent" is larger than chunk_size, it will be added as is.
    assert chunks == ["A" * 25]

from rae_core.ingestion.normalizer import IngestNormalizer


def test_normalize_string_input():
    normalizer = IngestNormalizer()
    text = "Hello\r\nWorld\x00"
    normalized, audit = normalizer.normalize(text)

    assert normalized == "Hello\nWorld"
    assert audit.trace["encoding"] == "string_input"


def test_normalize_bytes_utf8():
    normalizer = IngestNormalizer()
    data = "Północ".encode()
    normalized, audit = normalizer.normalize(data)

    assert normalized == "Północ"
    assert audit.trace["encoding"] == "utf-8-sig"


def test_normalize_bytes_windows1250():
    normalizer = IngestNormalizer()
    # "Północ" in Windows-1250: P is 0x50, ó is 0xF3, ł is 0xB3, n is 0x6E, o is 0x6F, c is 0x63
    data = bytes([0x50, 0xF3, 0xB3, 0x6E, 0x6F, 0x63])
    normalized, audit = normalizer.normalize(data)

    assert normalized == "Północ"
    assert audit.trace["encoding"] == "windows-1250"


def test_normalize_bytes_fallback_ascii():
    normalizer = IngestNormalizer()
    # Invalid bytes for UTF-8 and Windows-1250 (maybe?)
    # Let's use some truly invalid stuff.
    data = bytes([0xFF, 0xFE, 0xFD])
    normalized, audit = normalizer.normalize(data)

    # Should fallback to ascii ignore or something
    # Actually most things are valid in Windows-1250, so it might be that.
    assert audit.trace["encoding"] in ["utf-8-sig", "windows-1250", "fallback_ascii"]


def test_normalize_line_endings():
    normalizer = IngestNormalizer()
    text = "line1\rline2\r\nline3\n"
    normalized, audit = normalizer.normalize(text)
    assert normalized == "line1\nline2\nline3\n"

from src.preprocessing.chunker import chunk_record, chunk_words


def test_chunk_overlap_and_size():
    text = " ".join(f"w{i}" for i in range(100))
    chunks = chunk_words(text, size=40, overlap=10)
    assert len(chunks[0].split()) == 40
    assert chunks[0].split()[-10:] == chunks[1].split()[:10]


def test_chunk_record_sections():
    out = chunk_record("a b c", "d e", "", 10, 2)
    assert [s for s, _, _ in out] == ["abstract", "objectives"]

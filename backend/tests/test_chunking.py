from app.rag.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_is_single_chunk():
    assert chunk_text("hello world", chunk_size=100) == ["hello world"]


def test_long_text_splits_within_size_limit():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=200, overlap=40)

    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_chunks_overlap_and_cover_all_words():
    words = [f"word{i}" for i in range(300)]
    chunks = chunk_text(" ".join(words), chunk_size=150, overlap=30)

    covered = set()
    for chunk in chunks:
        covered.update(chunk.split())
    assert covered == set(words)

    first_tail = chunks[0].split()[-1]
    assert first_tail in chunks[1].split()


def test_always_makes_progress_with_large_overlap():
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=100, overlap=99)

    assert len(chunks) > 1
    assert "".join(c[:1] for c in chunks)

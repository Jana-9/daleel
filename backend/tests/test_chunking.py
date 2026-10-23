from app.services.chunking import Page, TextBlock, chunk_document, chunk_page


def block(text: str, y: float = 0) -> TextBlock:
    return TextBlock(text, (0, y, 100, y + 10))


def sentence(n: int) -> str:
    return f"الجملة رقم {n} في هذه الصفحة تشرح قاعدة من قواعد الجامعة."  # ~55 chars


def test_short_page_becomes_one_chunk():
    page = Page(1, [block("سطر أول"), block("سطر ثاني")])
    chunks = chunk_page(page, size=200, overlap=0)
    assert len(chunks) == 1
    assert chunks[0].content == "سطر أول سطر ثاني"
    assert chunks[0].page_number == 1
    assert len(chunks[0].bboxes) == 2


def test_chunks_respect_the_size_limit():
    page = Page(1, [block(sentence(i), i * 10) for i in range(20)])
    chunks = chunk_page(page, size=200, overlap=0)
    assert len(chunks) > 1
    assert all(c.length <= 200 for c in chunks)
    # Without overlap, every block appears exactly once, in order.
    assert " ".join(c.content for c in chunks) == " ".join(sentence(i) for i in range(20))


def test_consecutive_chunks_overlap():
    page = Page(1, [block(sentence(i), i * 10) for i in range(20)])
    chunks = chunk_page(page, size=200, overlap=60)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.texts[0] == previous.texts[-1]


def test_chunks_never_cross_pages():
    pages = [Page(1, [block(sentence(1))]), Page(2, [block(sentence(2))])]
    chunks = chunk_document(pages, size=1000, overlap=100)
    assert [c.page_number for c in chunks] == [1, 2]


def test_a_block_longer_than_the_chunk_size_is_split_at_sentences():
    long_block = " ".join(f"جملة طويلة رقم {i}." for i in range(30))
    chunks = chunk_page(Page(3, [block(long_block)]), size=120, overlap=0)
    assert len(chunks) > 1
    assert all(c.length <= 120 for c in chunks)
    assert all(c.content.endswith(".") for c in chunks)
    assert all(c.page_number == 3 for c in chunks)


def test_empty_blocks_are_ignored():
    page = Page(1, [block("   "), block("\n"), block("نص")])
    assert [c.content for c in chunk_page(page, size=100, overlap=0)] == ["نص"]


def test_page_without_text_has_no_chunks():
    assert chunk_page(Page(1, []), size=100, overlap=0) == []

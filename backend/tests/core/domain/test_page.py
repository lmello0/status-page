from core.domain.page import Page


def test_page_iterates_over_content_in_order() -> None:
    page = Page(page_size=10, page_count=2, total_elements=2, total_pages=1, content=["a", "b"])

    assert list(page) == ["a", "b"]


def test_page_len_matches_content_size() -> None:
    page = Page(page_size=10, page_count=3, total_elements=3, total_pages=1, content=[1, 2, 3])

    assert len(page) == 3

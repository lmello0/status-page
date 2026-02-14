from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    page_size: int
    page_count: int
    total_elements: int
    total_pages: int
    content: list[T]

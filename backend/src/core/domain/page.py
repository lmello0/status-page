from dataclasses import dataclass
from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    page_size: int
    page_count: int
    total_elements: int
    total_pages: int
    content: list[T]

    def __iter__(self) -> Iterator[T]:
        return iter(self.content)

    def __len__(self) -> int:
        return len(self.content)

from typing import Generic, TypeVar

from infra.web.routers.schemas.product import CamelModel

T = TypeVar("T")


class PageDTO(CamelModel, Generic[T]):
    page_size: int
    page_count: int
    total_elements: int
    total_pages: int
    content: list[T]

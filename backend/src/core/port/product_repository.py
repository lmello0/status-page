from abc import ABC, abstractmethod
from typing import Optional

from core.domain.page import Page
from core.domain.product import Product


class ProductRepository(ABC):
    @abstractmethod
    async def save(self, product: Product) -> Product:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, product_id: int) -> Optional[Product]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Product]:
        raise NotImplementedError

    @abstractmethod
    async def find_all(self, is_visible: bool, page: int, page_size: int) -> Page[Product]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, product_id: int) -> bool:
        raise NotImplementedError

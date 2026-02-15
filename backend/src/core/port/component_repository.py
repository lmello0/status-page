from abc import ABC, abstractmethod
from typing import Optional

from core.domain.component import Component
from core.domain.page import Page


class ComponentRepository(ABC):
    @abstractmethod
    async def save(self, component: Component) -> Component:
        raise NotImplementedError

    @abstractmethod
    async def find_all_without_pagination(self) -> list[Component]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, component_id: int) -> Optional[Component]:
        raise NotImplementedError

    @abstractmethod
    async def find_all_by_product_id(self, product_id: int, page: int, page_size: int) -> Page[Component]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, component_id: int) -> bool:
        raise NotImplementedError

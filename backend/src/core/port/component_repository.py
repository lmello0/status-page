from abc import ABC
from typing import Optional

from core.domain.component import Component
from core.domain.page import Page


class ComponentRepository(ABC):
    async def save(self, component: Component) -> Component:
        raise NotImplementedError

    async def find_by_id(self, component_id: int) -> Optional[Component]:
        raise NotImplementedError

    async def find_all_by_product_id(self, product_id: int, page: int, page_size: int) -> Page[Component]:
        raise NotImplementedError

    async def delete(self, component_id: int) -> bool:
        raise NotImplementedError

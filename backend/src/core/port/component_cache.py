from abc import ABC, abstractmethod
from typing import Optional

from core.domain.component import Component


class ComponentCache(ABC):

    @abstractmethod
    async def set(self, component: Component) -> None:
        raise NotImplementedError

    async def get(self, component_id: int) -> Optional[Component]:
        raise NotImplementedError

    async def remove(self, component_id: int) -> None:
        raise NotImplementedError

    async def get_all(self) -> dict[int, Component]:
        raise NotImplementedError

    async def clear(self) -> None:
        raise NotImplementedError

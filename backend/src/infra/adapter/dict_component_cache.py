import asyncio
from functools import lru_cache
from typing import Optional

from core.domain.component import Component
from core.port.component_cache import ComponentCache


class DictComponentCache(ComponentCache):
    def __init__(self) -> None:
        self._components = {}
        self._lock = asyncio.Lock()

    async def set(self, component: Component) -> None:
        async with self._lock:
            self._components[component.id] = component

    async def get(self, component_id: int) -> Optional[Component]:
        async with self._lock:
            return self._components.get(component_id)

    async def remove(self, component_id: int) -> None:
        async with self._lock:
            self._components.pop(component_id, None)

    async def get_all(self) -> dict[int, Component]:
        async with self._lock:
            return self._components.copy()

    async def clear(self) -> None:
        async with self._lock:
            self._components.clear()


@lru_cache
def get_dict_component_cache() -> ComponentCache:
    return DictComponentCache()

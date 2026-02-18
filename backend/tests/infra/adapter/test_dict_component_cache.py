import pytest

from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from infra.adapter.dict_component_cache import DictComponentCache


def _component(component_id: int, *, is_active: bool = True) -> Component:
    return Component(
        id=component_id,
        product_id=1,
        name=f"component-{component_id}",
        type=ComponentType.BACKEND,
        monitoring_config=HealthcheckConfig(health_url=f"https://service-{component_id}.example.com/health"),
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_dict_component_cache_set_get_remove_and_clear() -> None:
    cache = DictComponentCache()
    component = _component(1)

    await cache.set(component)
    cached = await cache.get(1)
    assert cached is not None
    assert cached.name == "component-1"

    all_components = await cache.get_all()
    assert list(all_components.keys()) == [1]

    await cache.remove(1)
    assert await cache.get(1) is None

    await cache.set(component)
    await cache.clear()
    assert await cache.get_all() == {}

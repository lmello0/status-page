import infra.adapter.dict_component_cache as cache_module
import infra.adapter.local_scheduler as scheduler_module
import infra.adapter.postgres_component_repository as component_repo_module
import infra.adapter.postgres_log_repository as log_repo_module
import infra.adapter.postgres_product_repository as product_repo_module


def test_get_product_repository_is_cached(monkeypatch) -> None:
    fake_session_factory = object()
    product_repo_module.get_product_repository.cache_clear()
    monkeypatch.setattr(product_repo_module, "get_session_factory", lambda: fake_session_factory)

    first = product_repo_module.get_product_repository()
    second = product_repo_module.get_product_repository()

    assert first is second
    assert first._session_factory is fake_session_factory


def test_get_component_repository_is_cached(monkeypatch) -> None:
    fake_session_factory = object()
    component_repo_module.get_component_repository.cache_clear()
    monkeypatch.setattr(component_repo_module, "get_session_factory", lambda: fake_session_factory)

    first = component_repo_module.get_component_repository()
    second = component_repo_module.get_component_repository()

    assert first is second
    assert first._session_factory is fake_session_factory


def test_get_log_repository_is_cached(monkeypatch) -> None:
    fake_session_factory = object()
    log_repo_module.get_log_repository.cache_clear()
    monkeypatch.setattr(log_repo_module, "get_session_factory", lambda: fake_session_factory)

    first = log_repo_module.get_log_repository()
    second = log_repo_module.get_log_repository()

    assert first is second
    assert first._session_factory is fake_session_factory


def test_get_dict_component_cache_is_cached() -> None:
    cache_module.get_dict_component_cache.cache_clear()

    first = cache_module.get_dict_component_cache()
    second = cache_module.get_dict_component_cache()

    assert first is second


def test_get_local_scheduler_is_cached() -> None:
    scheduler_module.get_local_scheduler.cache_clear()

    first = scheduler_module.get_local_scheduler()
    second = scheduler_module.get_local_scheduler()

    assert first is second

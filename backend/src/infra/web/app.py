from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from infra.adapter.dict_component_cache import get_dict_component_cache
from infra.adapter.local_scheduler import get_local_scheduler
from infra.adapter.postgres_component_repository import get_component_repository
from infra.config.config import get_config
from infra.db.session import close_engine
from infra.logging.config import configure_logging
from infra.services.healthcheck_service import HealthcheckService
from infra.web.routers.component_router import router as component_router
from infra.web.routers.product_router import router as product_router
from infra.web.routers.stats_router import router as stats_router
from use_cases.component.get_all_components_unpaginated_use_case import (
    GetAllComponentsUnpaginatedUseCase,
)
from use_cases.component.update_component_status_use_case import (
    UpdateComponentStatusUseCase,
)


def create_app() -> FastAPI:
    config = get_config()

    configure_logging(
        log_level=config.LOGGING_CONFIG.LEVEL,
        json_logs=config.LOGGING_CONFIG.JSON_FORMAT,
        service_name=config.APP_NAME,
        environment=config.ENVIRONMENT,
    )

    scheduler = get_local_scheduler()
    cache = get_dict_component_cache()

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        follow_redirects=True,
    )

    component_repository = get_component_repository()

    healthcheck_service = HealthcheckService(
        sync_interval_seconds=config.SYNC_INTERVAL_SECONDS,
        scheduler=scheduler,
        cache=cache,
        http_client=http_client,
        get_components_use_case=GetAllComponentsUnpaginatedUseCase(component_repository),
        update_component_status_use_case=UpdateComponentStatusUseCase(component_repository),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        scheduler.start()
        await healthcheck_service.start()

        yield
        await close_engine()

        scheduler.stop()
        await http_client.aclose()

    app = FastAPI(
        title=config.APP_NAME,
        version=config.VERSION,
        root_path=config.ROOT_PATH,
        docs_url="/apidocs",
        lifespan=lifespan,
    )

    app.state.host = config.HOST
    app.state.port = config.PORT

    app.include_router(stats_router)
    app.include_router(product_router)
    app.include_router(component_router)

    return app

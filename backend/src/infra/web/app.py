from contextlib import asynccontextmanager

from fastapi import FastAPI

from infra.config.config import get_config
from infra.db.session import close_engine
from infra.logging.config import configure_logging
from infra.web.routers.product_router import router as product_router
from infra.web.routers.stats_router import router as stats_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_engine()


def create_app() -> FastAPI:
    config = get_config()

    configure_logging(
        log_level=config.LOGGING_CONFIG.LEVEL,
        json_logs=config.LOGGING_CONFIG.JSON_FORMAT,
        service_name=config.APP_NAME,
        environment=config.ENVIRONMENT,
    )

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

    return app

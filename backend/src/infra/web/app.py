from fastapi import FastAPI

from infra.logging.config import configure_logging
from infra.web.deps import get_config
from infra.web.routers.stats_router import router as stats_router


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
    )

    app.state.host = config.HOST
    app.state.port = config.PORT

    app.include_router(stats_router)

    return app

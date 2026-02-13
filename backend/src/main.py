import uvicorn

from infra.web.app import create_app

if __name__ == "__main__":
    app = create_app()

    uvicorn.run(
        app=app,
        host=app.state.host if "host" in app.state else "0.0.0.0",
        port=app.state.port if "port" in app.state else 8080,
        access_log=False,
        log_config=None,
    )

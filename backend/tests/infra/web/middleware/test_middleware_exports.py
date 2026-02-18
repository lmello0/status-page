import infra.web.middleware as middleware_module


def test_middleware_module_exports_request_event_middleware() -> None:
    assert "RequestEventLogMiddleware" in middleware_module.__all__

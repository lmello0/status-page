import logging
from time import perf_counter
from urllib.parse import parse_qsl
from uuid import uuid4

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from structlog.stdlib import BoundLogger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_logger = structlog.stdlib.get_logger("infra.web.request")
fallback_logger = logging.getLogger(__name__)


class RequestEventLogMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        request_id_header: str = "x-request-id",
        excluded_path_suffixes: set[str] | None = None,
    ) -> None:
        self.app = app
        self.request_id_header = request_id_header.lower()
        self.excluded_path_suffixes = excluded_path_suffixes or set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        if self._should_skip_path(path):
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        method = str(scope.get("method", ""))
        request_id = self._extract_or_generate_request_id(scope, header_name=self.request_id_header)
        request_metadata = self._build_request_metadata(scope)
        client_ip = self._extract_client_ip(scope)
        user_agent = self._extract_header(scope, "user-agent")
        history: list[dict[str, object]] = []

        route_path: str | None = None
        route_name: str | None = None
        route_logged = False

        response_status_code: int | None = None
        response_metadata: dict[str, object | None] = {
            "content_type": None,
            "content_length": None,
        }

        bind_contextvars(request_id=request_id, http_method=method, http_path=path)

        self._append_history(
            history,
            "request_received",
            started_at,
            {
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "request_metadata": request_metadata,
            },
        )

        def ensure_route_resolved() -> None:
            nonlocal route_logged, route_path, route_name

            if route_logged:
                return

            route_path, route_name = self._resolve_route(scope)
            route_logged = True

            self._append_history(
                history,
                "route_resolved",
                started_at,
                {
                    "route_path": route_path,
                    "route_name": route_name,
                },
            )

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status_code, response_metadata

            if message["type"] == "http.response.start":
                ensure_route_resolved()

                response_status_code = int(message.get("status", 200))

                headers = list(message.get("headers", []))
                headers = self._upsert_header(
                    headers=headers,
                    key=self.request_id_header.encode("latin-1"),
                    value=request_id.encode("latin-1"),
                )
                response_metadata = self._decode_response_headers(headers)

                self._append_history(
                    history,
                    "response_started",
                    started_at,
                    {
                        "status_code": response_status_code,
                        "response_metadata": response_metadata,
                    },
                )

                message = {**message, "headers": headers}

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as error:
            if response_status_code is None:
                # Ensure a canonical 500 response with request-id header is emitted once.
                await send_wrapper(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [],
                    }
                )
                await send_wrapper(
                    {
                        "type": "http.response.body",
                        "body": b"Internal Server Error",
                        "more_body": False,
                    }
                )

            ensure_route_resolved()

            response_status_code = response_status_code or 500
            duration_ms = self._elapsed_ms(started_at)

            error_payload = {
                "error_class": error.__class__.__name__,
                "error_message": str(error),
            }

            self._append_history(history, "exception_raised", started_at, error_payload)
            self._append_history(
                history,
                "request_completed",
                started_at,
                {
                    "status_code": response_status_code,
                    "outcome": "unhandled_exception",
                    "duration_ms": duration_ms,
                },
            )

            self._log_summary(
                status_code=response_status_code,
                had_exception=True,
                logger=request_logger,
                payload={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "route_path": route_path,
                    "route_name": route_name,
                    "status_code": response_status_code,
                    "outcome": "unhandled_exception",
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "request_metadata": request_metadata,
                    "response_metadata": response_metadata,
                    "history": history,
                    "error": error_payload,
                },
            )
            raise
        else:
            ensure_route_resolved()

            response_status_code = response_status_code or 200
            duration_ms = self._elapsed_ms(started_at)
            outcome = self._status_to_outcome(response_status_code)

            self._append_history(
                history,
                "request_completed",
                started_at,
                {
                    "status_code": response_status_code,
                    "outcome": outcome,
                    "duration_ms": duration_ms,
                },
            )

            error_payload: dict[str, object | None] | None = None
            if response_status_code >= 500:
                error_payload = {
                    "error_class": None,
                    "error_message": f"Server error response with status {response_status_code}",
                }

            self._log_summary(
                status_code=response_status_code,
                had_exception=False,
                logger=request_logger,
                payload={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "route_path": route_path,
                    "route_name": route_name,
                    "status_code": response_status_code,
                    "outcome": outcome,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "request_metadata": request_metadata,
                    "response_metadata": response_metadata,
                    "history": history,
                    "error": error_payload,
                },
            )
        finally:
            clear_contextvars()

    def _extract_or_generate_request_id(self, scope: Scope, header_name: str) -> str:
        request_id = self._extract_header(scope, header_name)

        if request_id:
            return request_id

        return str(uuid4())

    def _should_skip_path(self, path: str) -> bool:
        return any(path.endswith(suffix) for suffix in self.excluded_path_suffixes)

    def _build_request_metadata(self, scope: Scope) -> dict[str, object | None]:
        content_type = self._extract_header(scope, "content-type")
        raw_content_length = self._extract_header(scope, "content-length")

        content_length: int | None = None
        if raw_content_length and raw_content_length.isdigit():
            content_length = int(raw_content_length)

        raw_query = scope.get("query_string", b"")
        query_string = raw_query.decode("utf-8", errors="ignore") if isinstance(raw_query, bytes) else ""
        query_keys = sorted({key for key, _ in parse_qsl(query_string, keep_blank_values=True)})

        return {
            "content_type": content_type,
            "content_length": content_length,
            "query_keys": query_keys,
        }

    def _decode_response_headers(self, headers_raw: list[tuple[bytes, bytes]]) -> dict[str, object | None]:
        decoded_headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in headers_raw
        }

        content_length: int | None = None
        raw_content_length = decoded_headers.get("content-length")
        if raw_content_length and raw_content_length.isdigit():
            content_length = int(raw_content_length)

        return {
            "content_type": decoded_headers.get("content-type"),
            "content_length": content_length,
        }

    def _status_to_log_level(self, status_code: int, had_exception: bool) -> int:
        if had_exception:
            return logging.ERROR

        if status_code < 400:
            return logging.INFO

        if status_code < 500:
            return logging.WARNING

        return logging.ERROR

    def _append_history(
        self,
        history: list[dict[str, object]],
        name: str,
        started_at: float,
        details: dict[str, object] | None = None,
    ) -> None:
        event = {
            "event": name,
            "at_ms": self._elapsed_ms(started_at),
        }

        if details:
            event.update(details)

        history.append(event)

    def _resolve_route(self, scope: Scope) -> tuple[str | None, str | None]:
        route = scope.get("route")

        if route is None:
            return None, None

        route_path = getattr(route, "path", None)
        route_name = getattr(route, "name", None)

        return route_path, route_name

    def _extract_client_ip(self, scope: Scope) -> str | None:
        client = scope.get("client")
        if not client:
            return None

        return client[0]

    def _extract_header(self, scope: Scope, header_name: str) -> str | None:
        lookup = header_name.lower()
        headers = scope.get("headers", [])

        for raw_key, raw_value in headers:
            key = raw_key.decode("latin-1").lower()
            if key == lookup:
                return raw_value.decode("latin-1")

        return None

    def _upsert_header(self, headers: list[tuple[bytes, bytes]], key: bytes, value: bytes) -> list[tuple[bytes, bytes]]:
        normalized_key = key.lower()
        filtered_headers = [item for item in headers if item[0].lower() != normalized_key]
        filtered_headers.append((key, value))

        return filtered_headers

    def _elapsed_ms(self, started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 3)

    def _status_to_outcome(self, status_code: int) -> str:
        if status_code < 400:
            return "success"

        if status_code < 500:
            return "client_error"

        return "server_error"

    def _log_summary(
        self,
        *,
        status_code: int,
        had_exception: bool,
        logger: BoundLogger,
        payload: dict[str, object],
    ) -> None:
        log_level = self._status_to_log_level(status_code, had_exception)

        try:
            if had_exception:
                logger.exception("http_request_summary", **payload)
                return

            if log_level >= logging.ERROR:
                logger.error("http_request_summary", **payload)
                return

            if log_level >= logging.WARNING:
                logger.warning("http_request_summary", **payload)
                return

            logger.info("http_request_summary", **payload)
        except Exception:
            fallback_logger.exception("Failed to emit request summary log")

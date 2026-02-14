import os
import time
from datetime import datetime
from typing import Any

import psutil
from fastapi import APIRouter, Response, status

from infra.config.config import get_config
from infra.utils.formatters import format_bytes, format_time

router = APIRouter(prefix="/stats", tags=["Stats"])

_start_time: float = time.time()
_current_process: psutil.Process = psutil.Process(os.getpid())

_config = get_config()


@router.get(
    "/health",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get application health status",
)
async def get_health(response: Response):
    try:
        uptime = format_time(time.time() - _start_time)
        memory_info = _current_process.memory_full_info()

        ram = format_bytes(memory_info.rss)
        cpu_percent = _current_process.cpu_percent(interval=0.1)

        return {
            "status": "UP",
            "uptime": uptime,
            "app_name": _config.APP_NAME,
            "version": _config.VERSION,
            "ram": ram,
            "cpu_percent": cpu_percent,
            "timestamp": datetime.now(),
        }

    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "DEGRADED",
            "error": str(e),
            "timestamp": time.time(),
        }

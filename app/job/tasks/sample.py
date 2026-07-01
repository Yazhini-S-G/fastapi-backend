from collections.abc import Callable
from typing import TypeVar, cast

from celery import shared_task

from app import logger

MonitorTask = TypeVar("MonitorTask", bound=Callable[[], bool])
monitor_task = cast("Callable[[MonitorTask], MonitorTask]", shared_task(name="ping"))


@monitor_task
def monitor_target() -> bool:
    logger.info("Monitoring....")
    return True

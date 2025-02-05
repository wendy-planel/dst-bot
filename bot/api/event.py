"""消息事件"""

import structlog
from fastapi import APIRouter, Body, BackgroundTasks

from bot import models
from bot.schemas import Event
from bot.command import run_command
from bot.plugins import router as plugin_router


router = APIRouter()
log = structlog.get_logger()


@router.post(
    "",
    description="消息上报",
)
async def receive(
    background_tasks: BackgroundTasks,
    message: dict = Body(),
):
    log.info(message)
    try:
        event = Event.model_validate(message)
    except Exception:
        pass
    for item in event.message:
        if item.type == "file":
            await models.FileEvent.create(
                file=item.data.file,
                file_id=item.data.file_id,
            )
    background_tasks.add_task(run_command, plugin_router, event)
    return "ok"

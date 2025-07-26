import os
import asyncio

from aerich import Command
from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from bot.api import router
from bot.plugins import lobby
from bot.schedule import schedule
from bot.settings import (
    QQ,
    APP_NAME,
    TORTOISE_ORM,
    NAPCAT_CONFIG,
    NAPCAT_CONFIG_PATH,
)


def write_napcat_config():
    if NAPCAT_CONFIG_PATH and not os.path.exists(NAPCAT_CONFIG_PATH):
        with open(f"{NAPCAT_CONFIG_PATH}/onebot11_{QQ}.json", "w") as file:
            file.write(NAPCAT_CONFIG)


async def lifespan(app: FastAPI):
    command = Command(
        tortoise_config=TORTOISE_ORM,
        app=APP_NAME,
        location="./migrations",
    )
    await command.init()
    await command.upgrade(run_in_transaction=True)
    register_tortoise(
        app,
        config=TORTOISE_ORM,
        add_exception_handlers=False,
    )
    write_napcat_config()
    asyncio.create_task(schedule.run())
    asyncio.create_task(lobby.update_lobby_room())
    asyncio.create_task(lobby.update_room_details())
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)

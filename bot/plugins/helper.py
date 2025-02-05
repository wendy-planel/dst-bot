import datetime

import httpx

from bot import models
from bot.command import CommandRouter
from bot.schemas import Event, NodeMessage
from bot.settings import (
    WENDY_API,
    KLEI_TOKEN,
    NAPCAT_API,
)


router = CommandRouter()


@router.command("ls", inject_event=False)
async def ls():
    cluster_id = ""
    reply_message = "本群服务器如下: \n\n"
    async with httpx.AsyncClient(timeout=600) as client:
        url = f"{WENDY_API}/deploy?status=running"
        response = await client.get(url)
        for cluster in response.json():
            cluster_id = cluster["id"]
            cluster_name = cluster["cluster"]["ini"]["cluster_name"]
            reply_message += f"{cluster_id}. {cluster_name}\n"
    if cluster_id:
        reply_message += f"\n发送备份指令即可备份存至群文件如: 备份{cluster_id}\n"
        reply_message += "注意: 备份存档会引起游戏卡顿"
        return [NodeMessage(content=reply_message)]
    else:
        "404~~"


@router.command("开服.*+", limit_admin=True)
async def create(event: Event):
    args = event.match_message.removeprefix("开服")
    if "-" in args:
        cluster_name, cluster_password = args.split("-")
    else:
        cluster_name = args
        cluster_password = ""
    cluster_name = cluster_name
    cluster_password = cluster_password
    async with httpx.AsyncClient(timeout=600) as client:
        url = f"{WENDY_API}/deploy"
        post_data = {
            "cluster": {
                "cluster_token": KLEI_TOKEN,
                "ini": {
                    "cluster_name": cluster_name,
                    "max_players": 4,
                    "cluster_password": cluster_password,
                    "cluster_description": "QQ群: 908262651",
                },
            }
        }
        response = await client.post(url, json=post_data)
        response.raise_for_status()
    return "OK"


@router.command("重启[0-9]+", limit_admin=True)
async def restart(event: Event):
    id = event.match_message.removeprefix("重启")
    async with httpx.AsyncClient(timeout=600) as client:
        url = f"{WENDY_API}/deploy/restart/{id}"
        await client.get(url)
    return "OK"


@router.command("关服[0-9]+", limit_admin=True)
async def stop(event: Event):
    id = event.match_message.removeprefix("关服")
    async with httpx.AsyncClient(timeout=600) as client:
        url = f"{WENDY_API}/deploy/stop/{id}"
        await client.get(url)
    return "OK"


@router.command("文件开服.*+", limit_admin=True)
async def create_by_file(event: Event):
    file = event.match_message.removeprefix("文件开服")
    # 最近半小时内范围搜索
    now = datetime.datetime.now()
    constraints = {
        "file": file,
        "created_at__gte": now - datetime.timedelta(minutes=30),
    }
    event = await models.FileEvent.filter(**constraints).order_by("-created_at").first()
    if event is None:
        return "404~~"
    # 下载文件并上传开服
    async with httpx.AsyncClient(timeout=600) as client:
        post_data = {"file_id": event.file_id}
        response = await client.post(f"{NAPCAT_API}/get_file", json=post_data)
        response = response.json()
        # 找到并读取文件
        filepath = response["data"]["file"]
        with open(filepath, "rb") as file:
            files = {"file": (event.file, file.read())}
        response = await client.post(f"{WENDY_API}/deploy/upload", files=files)
        response.raise_for_status()
    return "OK"


@router.command("回档[0-9]+-[0-9]+", limit_admin=True)
async def rollback(event: Event):
    args = event.match_message.removeprefix("回档")
    id, days = args.split("-")
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.get(f"{WENDY_API}/deploy/{id}")
        response = response.json()
        world_name = "Master"
        for world in response["cluster"]["world"]:
            if world["type"] == "Master":
                world_name = world["name"]
        # 执行回滚
        post_data = {
            "command": f"c_rollback({days})",
            "world_name": world_name,
        }
        response = await client.post(
            f"{WENDY_API}/console/command/{id}", json=post_data
        )
        response.raise_for_status()
    return "OK"


@router.command("重置[0-9]+", limit_admin=True)
async def c_regenerateshard(event: Event):
    id = event.match_message.removeprefix("重置")
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.get(f"{WENDY_API}/deploy/{id}")
        response = response.json()
        world_name = "Master"
        for world in response["cluster"]["world"]:
            if world["type"] == "Master":
                world_name = world["name"]
        post_data = {
            "command": "c_regenerateshard()",
            "world_name": world_name,
        }
        response = await client.post(
            f"{WENDY_API}/console/command/{id}", json=post_data
        )
        response.raise_for_status()
    return "OK"

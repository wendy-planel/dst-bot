from typing import List, Literal, Dict, Any

import re
import asyncio
from datetime import datetime

import httpx
import structlog

from bot import constants
from bot.schedule import schedule
from bot.settings import KLEI_TOKEN
from bot.command import CommandRouter
from bot.schemas import Event, NodeMessage


log = structlog.get_logger()
# 限制读取房间详情的并发
semaphore = asyncio.Semaphore(6)


class LobbyRoomCache:
    def __init__(self) -> None:
        self._cache = {}

    def set(
        self,
        key: Literal["lobby_room", "room_details", "history_room"],
        data,
    ):
        self._cache[key] = {
            "data": data,
            "update_at": datetime.now().strftime("%Y-%m-%d-%H:%M"),
        }

    def get(
        self,
        key: Literal["lobby_room", "room_details", "history_room"],
    ) -> Dict[str, Any]:
        return self._cache.get(key)


global cache
router = CommandRouter()
cache = LobbyRoomCache()


async def read_room_details(
    row_id: str,
    region: str,
) -> dict:
    async with semaphore:
        room_details = {}
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://lobby-v2-{region}.klei.com/lobby/read"
                payload = {
                    "__token": KLEI_TOKEN,
                    "__gameId": "DST",
                    "query": {"__rowId": row_id},
                }
                response = await client.post(url, json=payload)
                if lobby_room := response.json().get("GET", []):
                    room_details = lobby_room[0]
                    room_details["region"] = region
        except Exception:
            pass
    return room_details


async def read_lobby_room(
    region: str,
) -> List[dict]:
    url = f"https://lobby-v2-cdn.klei.com/{region}-Steam.json.gz"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    rooms = []
    if lobby_room := response.json().get("GET", []):
        for item in lobby_room:
            item["region"] = region
            rooms.append(item)
    return rooms


async def read_regions() -> List[str]:
    async with httpx.AsyncClient() as client:
        url = "https://lobby-v2-cdn.klei.com/regioncapabilities-v2.json"
        response = await client.get(url)
    return [item["Region"] for item in response.json()["LobbyRegions"]]


@schedule.job(minutes=15)
async def update_lobby_room():
    log.info("[update_lobby_room]")
    rooms = []
    for region in await read_regions():
        region_rooms = await read_lobby_room(region)
        rooms.extend(region_rooms)
    global cache
    cache.set("lobby_room", rooms)


@schedule.job(hours=1)
async def update_room_details():
    log.info("[update_room_details]")
    rooms = []
    for region in await read_regions():
        row_ids = set()
        for room in await read_lobby_room(region):
            row_ids.add(room["__rowId"])
        tasks = []
        for row_id in row_ids:
            tasks.append(read_room_details(row_id, region))
        result = await asyncio.gather(*tasks)
        for room_details in result:
            if "__rowId" in room_details:
                rooms.append(room_details)
    cache.set("room_details", rooms)


@router.command("查房.*+")
async def find_lobby_room(event: Event):
    key = event.match_message.removeprefix("查房").strip()
    reply_message = ""
    if cache.get("lobby_room") is None:
        await update_lobby_room()
    count = 0
    history_room = {}
    lobby_room = cache.get("lobby_room")
    for room in lobby_room["data"]:
        name = room["name"]
        if key in name:
            count += 1
            history_room[count] = {
                "row_id": room["__rowId"],
                "region": room["region"],
            }
            reply_message += f"{count}.{room['name']}"
            reply_message += f"({room["connected"]}/{room["maxconnections"]})"
            reply_message += (
                f"{constants.season.get(room.get('season', ''), '未知季节')}"
            )
            mode = room.get("mode", "未知模式")
            reply_message += f"({constants.mode.get(mode, mode)})"
        if count > 6:
            break
    if count > 0:
        reply_message += "发送`.服务器序号`查询服务器详细信息，如:`.1`\n"
        cache.set("history_room", history_room)
        return reply_message
    else:
        return "404~~"


@router.command("查玩家.*+")
async def find_player_in_room(event: Event):
    key = event.match_message.removeprefix("查玩家").strip()
    count = 0
    history_room = {}
    reply_message = "查玩家结果如下(最多显示10条): \n\n"
    room_details = cache.get("room_details")
    if room_details is None:
        return "数据更新..."
    for room in room_details["data"]:
        name = room["name"]
        players = re.findall(r'name="(.*?)"', room["players"])
        day = re.findall(r"day=([0-9]+)", room.get("data", ""))
        day = day[0] if day else ""
        connected = room.get("connected", "")
        maxconnections = room.get("maxconnections", "")
        season = room.get("season", "")
        c_connect = f"""c_connect("{room.get('__addr', '')}", {room.get('port', '')})"""
        for player in players:
            if key in player:
                count += 1
                history_room[count] = {
                    "row_id": room["__rowId"],
                    "region": room["region"],
                }
                reply_message += f"编号: {count}\n"
                reply_message += f"存档: {name}\n"
                reply_message += f"玩家: {player}\n"
                reply_message += f"在线人数: {connected}/{maxconnections}\n"
                reply_message += f"天数: {day}\n"
                reply_message += f"季节: {season}\n"
                reply_message += f"直连: {c_connect}\n\n"
        if count >= 10:
            break
    if count > 0:
        reply_message += "发送`.服务器序号`查询服务器详细信息，如:`.1`\n"
        cache.set("history_room", history_room)
        return [NodeMessage(content=reply_message)]
    else:
        return "404~~"


@router.command("\.[0-9]+")
async def find_room_details_by_id(event: Event):
    key = event.match_message.removeprefix(".").strip()
    room = cache.get("history_room")["data"][int(key)]
    async with httpx.AsyncClient() as client:
        url = f'https://lobby-v2-{room["region"]}.klei.com/lobby/read'
        payload = {
            "__token": KLEI_TOKEN,
            "__gameId": "DST",
            "query": {"__rowId": room["row_id"]},
        }
        response = await client.post(url, json=payload)
        room = response.json()["GET"][0]
    name = room["name"]
    mode = room.get("mode", "")
    season = room.get("season", "")
    connected = room.get("connected", "")
    maxconnections = room.get("maxconnections", "")
    players = re.findall(r'name="(.*?)"', room["players"])
    roles = re.findall(r'prefab="(.*?)"', room["players"])
    day = re.findall(r"day=([0-9]+)", room.get("data", ""))
    day = day[0] if day else ""
    reply_message = f"[{name}](Steam)({connected}/{maxconnections})\n"
    reply_message += f"[天数]{day}{constants.season.get(season, '未知季节')}({constants.mode.get(mode, mode)})\n"
    reply_message += "🏆玩家列表🏆\n"
    index = 0
    for player, role in zip(players, roles):
        index += 1
        reply_message += f"{index}.{player}({constants.roles.get(role, role)})\n"
    reply_message += "📃模组列表📃\n"
    if room.get("mods"):
        mods = room.get("mods_info", [])
        mods = mods[1::5]
        for index, mod in enumerate(mods):
            reply_message += f"{index}.{mod}\n"
    else:
        reply_message += "无\n"
    return reply_message

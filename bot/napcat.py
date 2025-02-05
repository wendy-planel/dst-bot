from typing import Literal, List

import httpx
import structlog

from bot.settings import NAPCAT_API
from bot.schemas import Message, NodeMessage


log = structlog.get_logger()


async def download_file(url: str) -> str:
    """下载文件.

    Args:
        url (str): 文件下载地址.
        filename (str): 文件名.
        user_id (int | None): QQ.
        group_id (int | None): 群号.
        message_type (Literal["private", "group"]): 消息类型.

    Returns:
        str: 下载后保存的文件路径.
    """
    async with httpx.AsyncClient() as client:
        payload = {"url": url}
        response = await client.post(
            f"{NAPCAT_API}/download_file",
            json=payload,
            timeout=600,
        )
        return f'file://{response.json()["data"]["file"]}'


async def reply(
    message: str | Message | List[NodeMessage] | None,
    user_id: int | None = None,
    group_id: int | None = None,
    message_type: Literal["private", "group"] = "group",
):
    """回复消息.

    Args:
        message (str | Message | List[NodeMessage] | None): 消息.
        user_id (int | None): QQ.
        group_id (int | None): 群号.
        message_type (Literal["private", "group"]): 消息类型.
    """
    if not message:
        return
    if isinstance(message, (str, Message)):
        return await send_message(
            message,
            user_id=user_id,
            group_id=group_id,
            message_type=message_type,
        )
    if isinstance(message, list):
        return await forward_messages(
            message,
            user_id=user_id,
            group_id=group_id,
            message_type=message_type,
        )


async def send_message(
    message: str | Message | None,
    user_id: int | None = None,
    group_id: int | None = None,
    message_type: Literal["private", "group"] = "group",
):
    """发送消息.

    Args:
        message (str | Message | None): 消息.
        user_id (int | None): QQ.
        group_id (int | None): 群号.
        message_type (Literal["private", "group"]): 消息类型.
    """
    if isinstance(message, str):
        message = {
            "type": "text",
            "data": {
                "text": message,
            },
        }
    elif isinstance(message, Message):
        message = message.model_dump(mode="json")
    async with httpx.AsyncClient() as client:
        payload = {
            "message_type": message_type,
            "user_id": user_id,
            "group_id": group_id,
            "message": message,
        }
        response = await client.post(
            f"{NAPCAT_API}/send_msg",
            json=payload,
            timeout=600,
        )
    return response.json()


async def forward_messages(
    messages: List[NodeMessage],
    user_id: int | None = None,
    group_id: int | None = None,
    message_type: Literal["private", "group"] = "group",
) -> dict:
    """发送合并转发消息.

    Args:
        messages (List[NodeMessage]): 消息列表.
        user_id (int | None): QQ.
        group_id (int | None): 群号.
        message_type (Literal["private", "group"]): 消息类型.
    """

    action = f"{NAPCAT_API}/send_{message_type}_forward_msg"
    forward = []
    for message in messages:
        forward.append(
            {
                "type": "node",
                "data": {
                    "name": message.name,
                    "uin": message.uin,
                    "content": message.content,
                },
            }
        )
    async with httpx.AsyncClient() as client:
        payload = {
            "user_id": user_id,
            "group_id": group_id,
            "messages": forward,
        }
        response = await client.post(action, json=payload, timeout=600)
    return response.json()

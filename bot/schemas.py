from typing import Literal, List

from pydantic import BaseModel

from bot.settings import QQ


class FileMessage(BaseModel):
    file: str
    name: str = ""
    path: str = ""
    url: str = ""
    file_id: str = ""
    file_size: str = ""
    file_unique: str = ""


class TextMessage(BaseModel):
    text: str


class Message(BaseModel):
    type: Literal["file", "text"]
    data: FileMessage | TextMessage


class NodeMessage(BaseModel):
    name: str = "wendy"
    uin: str = QQ
    content: str


class Event(BaseModel):
    user_id: int | None = None
    group_id: int | None = None
    message_type: Literal["private", "group"]
    message: List[Message]
    time: int
    # 多条消息中匹配上的指令消息
    match_message: str | None = None

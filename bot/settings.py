import os

from datetime import tzinfo, timedelta


APP_NAME = "bot"
# 机器人QQ号
QQ = os.environ.get("QQ")
# wendy开服面板工具API  https://github.com/leiyi2000/wendy
WENDY_API = os.environ.get("WENDY_API")
# 科雷令牌
KLEI_TOKEN = os.environ.get("KLEI_TOKEN")
# napcat
NAPCAT_CONFIG = """{
  "network": {
    "websocketClients": [],
    "websocketServers": [],
    "httpSseServers": [],
    "httpClients": [
      {
        "name": "dst",
        "enable": true,
        "url": "http://dst-bot:8000/event",
        "messagePostFormat": "array",
        "reportSelfMessage": false,
        "token": "",
        "debug": false,
        "type": "HTTP 客户端"
      }
    ],
    "httpServers": [
      {
        "name": "napcat",
        "enable": true,
        "port": 3000,
        "host": "0.0.0.0",
        "enableCors": false,
        "enableWebsocket": false,
        "messagePostFormat": "array",
        "token": "",
        "debug": false
      }
    ],
    "plugins": []
  },
  "musicSignUrl": "",
  "enableLocalFile2Url": false,
  "parseMultMsg": true
}"""
NAPCAT_CONFIG_PATH = os.environ.get("NAPCAT_CONFIG_PATH")
NAPCAT_API = os.environ.get("NAPCAT_API", default="http://127.0.0.1:3000")
DATABASE_URL = os.environ.get("DATABASE_URL", default="sqlite://bot.sqlite3")


# 数据库配置
TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {
        APP_NAME: {
            "models": ["bot.models", "aerich.models"],
            "default_connection": "default",
        },
    },
    "timezone": "Asia/Shanghai",
}


class ShanghaiTZ(tzinfo):
    def __init__(self):
        self._offset = timedelta(hours=8)
        self._name = "Asia/Shanghai"

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self._name

    def dst(self, dt):
        return timedelta(0)


# 上海时区
SHANGHAI_TIMEZONE = ShanghaiTZ()

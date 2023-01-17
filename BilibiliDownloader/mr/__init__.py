"""本模块主要用于插件与movie-robot的交互与通信"""

# from mbot.openapi import mbot_api
from moviebotapi import MovieBotServer
from moviebotapi.core.session import AccessKeySession

SERVER_URL = "http://192.168.5.208:1329"
ACCESS_KEY = "6eUk9TKHOdnm8FqfZ5tWS0Dpj4xBLizX"

server = MovieBotServer(AccessKeySession(SERVER_URL, ACCESS_KEY))

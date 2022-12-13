import threading

from apscheduler.schedulers.blocking import BlockingScheduler
import asyncio
import logging

from mbot.core.plugins import plugin
from bilibili_api import sync, Credential
from mbot.openapi import mbot_api

from . import bilibili_main
from . import global_value
from . import bilibili_login

follow_uid_list = []
if_people_path, people_path = bilibili_main.Utils.if_get_character()
media_path = bilibili_main.Utils.get_media_path(False)
_LOGGER = logging.getLogger(__name__)
sched = BlockingScheduler()
server = mbot_api


def get_config(follow_uid):
    global follow_uid_list
    follow_uid_list = follow_uid


@plugin.task("retry_download", "重新下载之前报错的视频", cron_expression="*/8 * * * *")
def retry_download():
    # 重试下载
    _LOGGER.info("开始运行定时任务：查询是否有需要重试下载的id")
    asyncio.run(bilibili_main.retry_video())


@plugin.task("check_up_update", "查询追更的up主是否更新", cron_expression="*/5 * * * *")
def check_update():
    # 检查视频更新
    _LOGGER.info("开始运行定时任务：查询追更的up主是否更新")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    if not follow_uid_list:
        return
    for i in follow_uid_list:
        update = bilibili_main.ListenUploadVideo(
            i, if_people_path, media_path, people_path
        )
        tasks.append(update.listen_no_pages_video_new())
    loop.run_until_complete(asyncio.wait(tasks))


@plugin.task("check_cookie_is_valid", "检查cookie是否过期", cron_expression="*/30 * * * *")
def check_cookie_is_valid():
    # 检查cookie是否过期
    _LOGGER.info("开始运行定时任务：检查cookie是否过期")
    cookies = global_value.get_value("credential")
    if not global_value.get_value("is_cookie_valid"):
        _LOGGER.info("cookie还没设置，请重新登录")
        return
    elif sync(
            Credential(
                sessdata=cookies["SESSDATA"],
                bili_jct=cookies["bili_jct"],
                dedeuserid=cookies["DEDEUSERID"],
            ).check_valid()
    ):
        _LOGGER.info("cookie有效")
    else:
        _LOGGER.info("cookie已过期或没登录，请重新登录")
        global_value.set_value("is_cookie_valid", False)
        server.notify.send_text_message(
            title="b站cookie过期，请重新扫码登录", to_uid=1, body="请去mr的插件快捷功能页点击扫码登录按钮，并进行登陆"
        )

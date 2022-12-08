# from apscheduler.schedulers.blocking import BlockingScheduler
import asyncio
import logging

from mbot.core.plugins import plugin

import bilibili_main

follow_uid_list = []
if_people_path, people_path = bilibili_main.Utils.if_get_character()
media_path = bilibili_main.Utils.get_media_path(False)
_LOGGER = logging.getLogger(__name__)


def get_config(follow_uid):
    global follow_uid_list
    follow_uid_list = follow_uid


@plugin.task('retry_download', '重新下载之前报错的视频', cron_expression='*/10 * * * *')
def retry_download():
    # 重试下载
    _LOGGER.info("开始运行定时任务：查询是否有需要重试下载的id")
    asyncio.run(bilibili_main.retry_video())


@plugin.task('check_up_update', '查询追更的up主是否更新', cron_expression='*/5 * * * *')
def check_update():
    # 检查视频更新
    _LOGGER.info("开始运行定时任务：查询追更的up主是否更新")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    if not follow_uid_list:
        return
    for i in follow_uid_list:
        update = bilibili_main.ListenUploadVideo(i, if_people_path, media_path, people_path)
        tasks.append(update.listen_no_pages_video_new())
    loop.run_until_complete(asyncio.wait(tasks))

from apscheduler.schedulers.blocking import BlockingScheduler
import bilibili_main
import asyncio
import loguru

sched = BlockingScheduler()
follow_uid_list = [482324117]
emby_persons_path = "E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby"
if_get_character = True
media_path = r"E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby\123"
_LOGGER = bilibili_main._LOGGER


# @sched.scheduled_job('interval', minutes=20)
# def retry_download():
#     # 重试下载
#     asyncio.run(retry_video())


@sched.scheduled_job('interval', minutes=0.5)
def check_update():
    # 检查视频更新
    _LOGGER.info("检查更新")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    for i in follow_uid_list:
        update = bilibili_main.ListenUploadVideo(i, if_get_character, media_path, emby_persons_path)
        tasks.append(update.listen_no_pages_video_new())
    loop.run_until_complete(asyncio.wait(tasks))


sched.start()

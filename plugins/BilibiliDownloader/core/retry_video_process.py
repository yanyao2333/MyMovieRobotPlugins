from plugins.BilibiliDownloader.utils import global_value, files, LOGGER
from plugins.BilibiliDownloader.core import main_video_process
import asyncio
_LOGGER = LOGGER


async def retry_video_process(retry_video_number: int) -> bool:
    """重试视频下载

    :param retry_video_number: 重试视频数量
    :return: 是否重试成功
    """
    config = global_value.get_value("config")
    error_video_list = await files.ErrorVideoController().get_error_video_list()
    retry_video_number = min(retry_video_number, len(error_video_list))
    tasks = []
    if retry_video_number == 0:
        return True
    for i in range(retry_video_number):
        error_video = error_video_list[i]
        if error_video["retry"] >= 10:
            await files.ErrorVideoController().remove_error_video(error_video["bvid"], error_video["page"])
            _LOGGER.warning(f"视频{error_video['bvid']}重试次数已达上限，跳过")
            continue
        task = main_video_process.SaveOneVideo(mode=config.get("video_save_mode"), bvid=error_video["bvid"], media_path=config.get("media_path"), scraper_people=config.get("person_dir") if config.get("person_dir") else False, emby_people_path=config.get("person_dir")).run()
        task = asyncio.create_task(task)
        tasks.append(task)
        # await files.ErrorVideoController().remove_error_video(error_video["bvid"], error_video["page"])
    if len(tasks) == 0:
        return True
    res = await asyncio.gather(*tasks)
    for i in range(retry_video_number):
        if res[i]:
            _LOGGER.info(f"视频{error_video_list[i]['bvid']}重试成功")
            await files.ErrorVideoController().remove_error_video(error_video_list[i]["bvid"], error_video_list[i]["page"])
        elif not res[i]:
            _LOGGER.warning(f"视频{error_video_list[i]['bvid']}重试失败")
    if False in res:
        return False
    return True
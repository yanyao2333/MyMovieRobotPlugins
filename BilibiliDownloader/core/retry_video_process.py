from BilibiliDownloader.utils import files


async def retry_video() -> bool:
    """
    重试下载之前失败的视频 被定时任务调用 每次最多重试1个 防止被封ip
    保佑用户不会被封ip，shark个陈睿来祭天吧
    """
    file_controller = files.ErrorVideoController()
    retry_list = await file_controller.get_error_video_list()
    if len(retry_list) == 0:
        return True
    for video in retry_list:
        if video["retry_times"] < 5:
            video["retry_times"] += 1
            await file_controller.update_error_video_list(retry_list)
            return True
        else:
            await file_controller.delete_error_video(video["av"])
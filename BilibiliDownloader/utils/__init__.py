"""工具"""

import traceback
import asyncio
import loguru
import logging
from typing import Any, Callable
from functools import wraps
import logging
import sys

from . import files

LOGGER = loguru.logger  # 定义全局使用的日志记录器


def handle_error(
    record_error_video: bool = False,
    remove_error_video_folder: bool = False,
    record_video_bvid: str = None,
    record_video_page: int = 0,
    remove_error_video_path: str = None,
):
    """捕捉函数错误

    :param record_error_video: 是否记录错误视频
    :param remove_error_video_folder: 是否删除错误视频文件夹
    :param record_video_bvid: 记录错误视频的bvid
    :param record_video_page: 记录错误视频的分p号
    :param remove_error_video_path: 删除错误视频的路径
    """

    def log(func: Callable[..., Any]):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def coroutine_func_handle(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except:
                    tracelog = traceback.format_exc()
                    LOGGER.error(f"函数 {func.__name__} 报错")
                    LOGGER.error(f"报错日志：\n{tracelog}")
                    if record_error_video:
                        await files.ErrorVideoController().write_error_video(
                            record_video_bvid, record_video_page
                        )
                    elif remove_error_video_folder:
                        await files.delete_video_folder(remove_error_video_path)

            return coroutine_func_handle
        else:

            @wraps(func)
            def sync_func_handle(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except:
                    # 输出tracelog
                    tracelog = traceback.format_exc()
                    LOGGER.error(f"函数 {func.__name__} 报错")
                    LOGGER.error(f"报错日志：\n{tracelog}")
                    if record_error_video:
                        files.ErrorVideoController().write_error_video(
                            record_video_bvid, record_video_page
                        )
                    elif remove_error_video_folder:
                        files.delete_video_folder(remove_error_video_path)

            return sync_func_handle

    return log
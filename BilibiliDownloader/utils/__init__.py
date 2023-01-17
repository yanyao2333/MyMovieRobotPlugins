"""工具"""

import traceback
import asyncio
import loguru
import logging
from typing import Any, Callable
from functools import wraps
import logging
import sys

LOGGER = loguru.logger  # 定义全局使用的日志记录器


def handle_error(
    record_error_video: bool = False,
    remove_error_video_folder: bool = False,
    record_video_bvid: str = None,
    record_video_page: int = 0,
):
    """捕捉函数错误

    Args:
        record_error_video (bool, optional): 是否记录错误视频id Defaults to False.
        remove_error_video_folder (bool, optional): 是否删除错误视频所指向的文件夹 Defaults to False.
        record_video_bvid (str, optional): 需要记录的bvid Defaults to None.
        record_video_page (int, optional): 需要记录的分p号 Defaults to 0.
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
                        # TODO 完善后续处理
                        pass
                    elif remove_error_video_folder:
                        # TODO 完善后续处理
                        pass

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
                        # TODO 完善后续处理
                        pass
                    elif remove_error_video_folder:
                        # TODO 完善后续处理
                        pass

            return sync_func_handle

    return log
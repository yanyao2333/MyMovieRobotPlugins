"""操作文件"""

import aiofiles
from aiofiles import os as aios
from . import global_value
from . import LOGGER

local_path = global_value.get_value("local_path") + "/data"
if await aios.path.exists(local_path):
    await aios.makedirs(local_path, exist_ok=True)
_LOGGER = LOGGER


class ErrorVideoFileControl:
    def __init__(self) -> None:
        """
        error_video.txt文件控制
        """
        if not aios.path.exists(f"{local_path}/error_video.txt"):
            _LOGGER.info("error_video.txt 文件未创建，创建1下")
            f = open(f"{local_path}/error_video.txt")
            f.close()
        self.local_path = local_path + "/error_video.txt"

    async def write_error_video(self, bvid: str, page: int = 0):
        """写入错误记录

        :param bvid: 视频的bvid号
        :param page: 分p号，从0开始
        """
        async with aiofiles.open(self.local_path, "a") as f:
            await f.write(f"{bvid} P{str(page)}\n")
            _LOGGER.info(f"写入error_video.txt成功，内容：{bvid} P{str(page)}")
            await f.close()

    async def read_error_video(self, bvid: str, page: int = 0) -> bool:
        """根据bvid查找错误记录

        :param bvid: 视频的bvid号
        :param page: 分p号，从0开始
        :return: 是否存在
        """
        async with aiofiles.open(self.local_path, "r") as f:
            error_video = await f.readlines()
            if error_video:
                for i in error_video:
                    if f"{bvid} P{str(page)}\n" in i:
                        return True
                    else:
                        return False
            else:
                return False

    async def remove_error_video(self, bvid: str):
        """删除一条错误记录

        :param bvid: 视频的bvid号
        """
        async with aiofiles.open(self.local_path, "r") as f:
            lines = await f.readlines()
        async with aiofiles.open(self.local_path, "w") as f_w:
            for line in lines:
                if bvid not in line:
                    await f_w.write(line)

    async def get_error_video_list(self) -> list[str]:
        """获取错误列表

        Returns:
            list: 错误视频列表，每项包含bvid+page
        """
        async with aiofiles.open(self.local_path, "r") as f:
            lines = await f.readlines()
        error_video_list = []
        for line in lines:
            error_video_list.append(line.replace("\n", ""))
        return error_video_list

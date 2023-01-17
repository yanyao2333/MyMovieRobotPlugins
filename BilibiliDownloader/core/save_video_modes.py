import enum
import os

import aiofiles
from aiofiles import os as aios

from . import process_video, nfo_generator
from BilibiliDownloader.utils import others, LOGGER, global_value

_LOGGER = LOGGER
NoRetry = "NoRetry"

class SaveVideoMode(enum.Enum):
    """保存视频的文件夹样式"""
    UP_FOLDER_STYLE = 0  # 按照up主分组保存
    NORMAL_STYLE = 1  # 按照电影格式保存


class SaveOneVideo:
    def __init__(self, mode: SaveVideoMode, bvid: str, media_path: str, scraper_people: bool, emby_people_path: str = None):
        """下载视频入口函数

        :param mode: 保存视频的文件夹样式
        :param bvid: 视频bvid
        :param media_path: 媒体库路径（所有视频公用路径）
        :param scraper_people: 是否刮削up主
        :param emby_people_path: up主文件夹路径
        """
        self.video_object = None
        self.title = None
        self.video_info = None
        self.mode = mode
        self.bvid = bvid
        self.media_path = media_path
        self.scraper_people = scraper_people
        self.emby_people_path = emby_people_path

    async def get_video_info(self):
        """获取视频信息"""
        res = await process_video.get_video_info(self.bvid)
        if not res:
            return NoRetry
        self.video_info, self.video_object = res
        self.title = self.video_info["title"]

    async def _save_up_folder_style_video(self):
        path = f"{self.media_path}/{self.video_info['owner']['name']}/Season 1/{self.title}"
        tmp_path = f"{self.media_path}/tmp/{self.title}"
        _LOGGER.info(f"视频保存路径：{path}")
        if not await aios.path.exists(path):
            os.makedirs(path)
        if not await aios.path.exists(tmp_path):
            os.makedirs(tmp_path)
        await process_video.ProcessNormalVideo(bvid=self.bvid, video_path=tmp_path, scraper_people=self.scraper_people, emby_people_path=self.emby_people_path).run()
        await aios.rename(tmp_path, path)
        await nfo_generator.NfoGenerator(self.video_info, 0).gen_tvshow_nfo()



    async def run(self):
        if not await aios.path.exists(f"{self.media_path}/tmp"):
            os.makedirs(f"{self.media_path}/tmp")




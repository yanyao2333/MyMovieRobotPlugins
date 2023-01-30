import enum
import os

import aiofiles
from aiofiles import os as aios

from . import process_video, nfo_generator, public_function
from ..utils import LOGGER, files

_LOGGER = LOGGER


class SaveVideoMode(enum.Enum):
    """保存视频的文件夹样式"""
    UP_FOLDER_STYLE = 0  # 按照up主分组保存
    NORMAL_STYLE = 1  # 按照电影格式保存


class SaveOneVideo:
    def __init__(self, mode: SaveVideoMode, bvid: str, media_path: str, scraper_people: bool,
                 emby_people_path: str = None):
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
            return False
        self.video_info, self.video_object = res
        self.title = self.video_info["title"]
        self.folder_name = self.video_info['owner']['name'] + "-" + str(self.video_info["owner"]["mid"])

    async def get_uploader_info(self):
        self.uploader_info = await public_function.get_uploader_info(self.video_info["owner"]["mid"])

    async def _save_uploader_folder_style_video(self):
        path = f"{self.media_path}/{self.folder_name}/Season 1/{self.title}"
        tmp_path = f"{self.media_path}/tmp/{self.title}"
        _LOGGER.info(f"视频保存路径：{path}")
        if not await aios.path.exists(path):
            os.makedirs(path)
        if not await aios.path.exists(tmp_path):
            os.makedirs(tmp_path)
        await process_video.ProcessNormalVideo(bvid=self.bvid, video_path=tmp_path, scraper_people=self.scraper_people,
                                               emby_people_path=self.emby_people_path, video_info=self.video_info,
                                               video_object=self.video_object).run()
        await self._move_video_to_folder(path)
        await aios.remove(path + f"/{self.title}.nfo")
        nfo = nfo_generator.NfoGenerator(self.uploader_info, uploader_folder_mode=True)
        tvshow = await nfo.gen_tvshow_nfo_by_uploader()
        await nfo.save_nfo(tvshow, path + "/../../tvshow.nfo")
        video_num = await files.count_folder_num(path + "/../")
        nfo = nfo_generator.NfoGenerator(self.video_info, page=video_num-1)
        episode_detail = await nfo.gen_episodedetails_nfo()
        await nfo.save_nfo(episode_detail, path + f"/{self.title}.nfo")

    async def _move_video_to_folder(self, path):
        """移动全部文件到指定文件夹并删除tmp文件夹"""
        for file in os.listdir(f"{self.media_path}/tmp/{self.title}"):
            await aios.rename(f"{self.media_path}/tmp/{self.title}/{file}", f"{path}/{file}")
        await aios.removedirs(f"{self.media_path}/tmp/{self.title}")



    async def run(self):
        if not await aios.path.exists(f"{self.media_path}/tmp"):
            os.makedirs(f"{self.media_path}/tmp")
        await self.get_video_info()
        if self.mode == SaveVideoMode.UP_FOLDER_STYLE:
            await self.get_uploader_info()
            await self._save_uploader_folder_style_video()

import enum
import os
import shutil

from aiofiles import os as aios

from plugins.BilibiliDownloader.core import nfo_generator, public_function, process_video
from plugins.BilibiliDownloader.mr import mr_notify
from plugins.BilibiliDownloader.utils import LOGGER, files

_LOGGER = LOGGER


class SaveVideoMode(enum.Enum):
    """保存视频的文件夹样式"""
    UP_FOLDER_STYLE = 0  # 按照up主分组保存
    NORMAL_STYLE = 1  # 按照电影格式保存


class SaveOneVideo:
    bvid = ""
    page = 0
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
        SaveOneVideo.bvid = bvid

    async def get_video_info(self):
        """获取视频信息"""
        res = await public_function.get_video_info(self.bvid)
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
        await aios.rename(path + "/poster.jpg", path + f"/{self.title}-thumb.jpg")
        await aios.remove(path + "/fanart.jpg")
        nfo = nfo_generator.NfoGenerator(self.uploader_info, uploader_folder_mode=True)
        tvshow = await nfo.gen_tvshow_nfo_by_uploader()
        if await aios.path.exists(path + "/../../tvshow.nfo"):
            await aios.remove(path + "/../../tvshow.nfo")
        await nfo.save_nfo(tvshow, path + "/../../tvshow.nfo")
        video_num = await files.count_folder_num(path + "/../")
        nfo = nfo_generator.NfoGenerator(self.video_info, page=video_num-1)
        episode_detail = await nfo.gen_episodedetails_nfo()
        await nfo.save_nfo(episode_detail, path + f"/{self.title}.nfo")
        await public_function.download_uploader_face(self.uploader_info["face"], path + "/../../", "fanart")
        shutil.copy(path + "/../../" + "fanart.jpg", path + "/../../" + "poster.jpg")
        _LOGGER.info(f"视频保存成功：{path}")

    async def _save_normal_style_video(self):
        tmp_path = f"{self.media_path}/tmp/{self.title}"
        path = f"{self.media_path}/{self.title}"
        _LOGGER.info(f"视频保存路径：{path}")
        if not await aios.path.exists(path):
            os.makedirs(path)
        if not await aios.path.exists(tmp_path):
            os.makedirs(tmp_path)
        # raise Exception("这是一个人为制造的异常，用于测试异常处理")
        await process_video.ProcessNormalVideo(bvid=self.bvid, video_path=tmp_path, scraper_people=self.scraper_people,
                                               emby_people_path=self.emby_people_path, video_info=self.video_info,
                                               video_object=self.video_object).run()
        await self._move_video_to_folder(path)
        _LOGGER.info(f"视频保存成功：{path}")

    async def _move_video_to_folder(self, path):
        """移动全部文件到指定文件夹并删除tmp文件夹"""
        for file in os.listdir(f"{self.media_path}/tmp/{self.title}"):
            await aios.rename(f"{self.media_path}/tmp/{self.title}/{file}", f"{path}/{file}")
        await aios.removedirs(f"{self.media_path}/tmp/{self.title}")


    # @decorators.handle_error(record_error_video=True, remove_error_video_folder=True, record_video_bvid=bvid, remove_error_video_path=f"{self.media_path}/tmp/{self.title}")
    async def run(self):
        try:
            _LOGGER.info(f"下载刮削程序启动：{self.bvid}")
            if not await aios.path.exists(f"{self.media_path}/tmp"):
                os.makedirs(f"{self.media_path}/tmp")
            await self.get_video_info()
            if self.mode == SaveVideoMode.UP_FOLDER_STYLE:
                _LOGGER.info(f"视频保存模式：UP主文件夹模式 干活了干活了")
                await self.get_uploader_info()
                await self._save_uploader_folder_style_video()
            elif self.mode == SaveVideoMode.NORMAL_STYLE:
                _LOGGER.info(f"视频保存模式：普通模式 干活了干活了")
                await self._save_normal_style_video()
        except Exception:
            _LOGGER.exception(f"下载刮削程序错误：{self.bvid}，删除文件目录，等待重试")
            if await files.ErrorVideoController().write_error_video(self.bvid, self.page) is False:
                _LOGGER.error(f"写入错误视频文件失败：{self.bvid}，请按照上方错误信息检查错误原因，该视频下载任务跳过并发送下载失败通知")
                await mr_notify.Notify(self.video_info).send_error_video_notify()
            if await aios.path.exists(f"{self.media_path}/tmp/{self.title}"):
                _LOGGER.info(f"删除tmp文件夹中的当前视频目录")
                await files.delete_video_folder(f"{self.media_path}/tmp/{self.title}")
            _LOGGER.info(f"删除视频文件夹")
            if self.mode == SaveVideoMode.UP_FOLDER_STYLE:
                if await aios.path.exists(f"{self.media_path}/{self.folder_name}/Season 1/{self.title}"):
                    await files.delete_video_folder(f"{self.media_path}/{self.folder_name}/Season 1/{self.title}")
            if self.mode == SaveVideoMode.NORMAL_STYLE:
                if await aios.path.exists(f"{self.media_path}/{self.title}"):
                    await files.delete_video_folder(f"{self.media_path}/{self.title}")

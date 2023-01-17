"""核心部分，控制视频下载刮削流程"""
import shutil
import sys

from aiofiles import os

from utils import global_value, LOGGER, handle_error
from . import nfo_generator
from .public_function import (
    get_video_info,
    download_video,
    download_subtitle,
    download_video_cover,
    downlod_ass_danmakus,
    download_people_image,
)

local_path = global_value.get_value("local_path")
_LOGGER = LOGGER
NoRetry = "NoRetry"


# sys.stdout = LOGGER.handle[0].flush()


class ProcessNormalVideo:
    bvid = ""
    path = ""

    def __init__(
        self,
        bvid: str,
        video_path: str,
        scraper_people: bool,
        emby_people_path: str = None,
        video_info: dict = None,
        video_object: object = None,
    ):
        """单视频下载刮削流程

        :param bvid: 视频bvid
        :param video_path: 视频保存路径
        :param scraper_people: 是否刮削人物
        :param emby_people_path: emby人物文件夹路径
        :param video_info: 视频信息
        :param video_object: 视频对象
        """
        self.pretty_title = None
        self.title = None
        self.video_object = None
        self.video_info = None
        self.bvid = bvid
        self.video_path = video_path
        self.scraper_people = scraper_people
        self.emby_people_path = emby_people_path
        ProcessNormalVideo.bvid = bvid
        ProcessNormalVideo.path = video_path

    async def check_args(self):
        """检查参数是否合法"""
        if await os.path.exists(self.video_path):
            _LOGGER.info(f"下载目录已存在，删掉！")
            shutil.rmtree(self.video_path)
        await os.makedirs(self.video_path, exist_ok=True)
        if self.scraper_people and self.emby_people_path is None:
            _LOGGER.error("开启了人物刮削，但未指定emby人物文件夹路径")
            return NoRetry
        elif await os.path.exists(self.emby_people_path) is False:
            _LOGGER.error("emby人物文件夹不存在，请检查是否将emby人物文件夹挂载到了mr容器中，并检查是否输入错误")
            return NoRetry

    async def get_video_info(self) -> str | bool:
        """获取视频信息

        :return: 是否成功
        """
        if self.video_info and self.video_object:
            _LOGGER.info(f"已有视频信息，跳过获取视频信息步骤")
        else:
            res = await get_video_info(self.bvid)
            _LOGGER.info(f"视频信息为：{res}")
            if res is False:
                _LOGGER.error("获取视频信息失败")
                return NoRetry
            self.video_info, self.video_object = res
        self.title = self.video_info["title"].replace("/", " ")
        self.pretty_title = " 「" + self.title + "」 "
        if len(self.video_info["pages"]) > 1:
            _LOGGER.error("视频为多P视频，请使用ProcessPagesVideo类进行处理，这不归我管~")
            return NoRetry
        return True

    async def download(self) -> bool | str:
        """下载视频

        Returns:
            bool: 是否下载成功
        """
        _LOGGER.info(f"开始下载视频：{self.pretty_title}")
        _title = self.title
        if len(self.title) > 250:
            _title = self.title[:220]
            _LOGGER.warning(f"视频标题过长，已截取前220个字符作为视频文件名：{_title}")
        res = await download_video(
            video_object=self.video_object,
            dst=self.video_path,
            filename=_title,
        )
        if res is False:
            return False
        elif res is NoRetry:
            return NoRetry
        _LOGGER.info(f"视频下载完成：{self.pretty_title}")
        return True

    async def scraper(self) -> bool:
        """刮削视频

        Returns:
            bool: 是否刮削成功
        """
        _LOGGER.info(f"开始刮削视频：{self.pretty_title}")
        _LOGGER.info("开始生成nfo文件")
        scraper = nfo_generator.NfoGenerator(self.video_info)
        path = f"{self.video_path}/{self.title}.nfo"
        if len(self.title) > 250:
            _title = self.title[:220]
            _LOGGER.warning(f"视频标题过长，已截取前220个字符作为nfo文件名：{_title}")
            path = f"{self.video_path}/{_title}.nfo"
        tree = await scraper.gen_movie_nfo()
        await scraper.save_nfo(tree, path)
        _LOGGER.info(f"nfo文件生成完成，保存路径为：{path}")
        _LOGGER.info("开始下载视频封面")
        await download_video_cover(self.video_info, self.video_path, "poster")
        await download_video_cover(self.video_info, self.video_path, "fanart")
        _LOGGER.info("视频封面下载完成")
        _LOGGER.info(f"视频刮削完成：{self.pretty_title}")
        return True

    async def scraper_people_folder(self) -> bool:
        """刮削up主

        Returns:
            bool: 是否刮削成功
        """
        if self.scraper_people is False:
            return True
        _LOGGER.info(f"开始刮削up主：{self.pretty_title}")
        scraper = nfo_generator.NfoGenerator(self.video_info)
        tree = await scraper.gen_people_nfo()
        for key in tree:
            parent_people_folder = f"{self.emby_people_path}/{key[0]}"
            people_folder = f"{parent_people_folder}/{key}"
            if await os.path.exists(parent_people_folder) is False:
                _LOGGER.info(f"创建人物文件夹：{people_folder}")
                await os.makedirs(people_folder)
            elif await os.path.exists(people_folder) is False:
                _LOGGER.info(f"创建人物文件夹：{people_folder}")
                await os.makedirs(people_folder)
            else:
                _LOGGER.info(f"人物文件夹已存在：{people_folder} 跳过处理")
                continue
            await scraper.save_nfo(tree[key], f"{people_folder}/person.nfo")
            await download_people_image(self.video_info, people_folder, "folder", key)
            _LOGGER.info(f"人物 {key} 刮削完成：{people_folder}")
        _LOGGER.info(f"up主刮削完成：{self.pretty_title}")
        return True

    async def save_danmakus(self) -> bool | str:
        """保存弹幕

        Returns:
            bool: 是否保存成功
        """
        _LOGGER.info(f"开始保存弹幕：{self.pretty_title}")
        res = await downlod_ass_danmakus(self.video_object, self.video_path, self.title)
        if res is False:
            _LOGGER.info(f"弹幕消失在了虚空中！请尝试自行下载")
            return True
        _LOGGER.info(f"弹幕保存完成：{self.pretty_title}")
        return True

    async def save_subtitles(self) -> bool | str:
        """保存字幕

        Returns:
            bool: 是否保存成功
        """
        _LOGGER.info(f"开始保存字幕：{self.pretty_title}")
        subtitle_list = self.video_info["subtitle"]["list"]
        if len(subtitle_list) == 0:
            _LOGGER.info(f"视频没有字幕")
            return True
        _LOGGER.info(f"视频有 {len(subtitle_list)} 个字幕，开始处理")
        for subtitle in subtitle_list:
            if "ai" in subtitle["lan"]:
                _LOGGER.info(
                    f"这个字幕为AI字幕，语言代码为：{subtitle['lan']}，中文名称为：{subtitle['lan_doc']}，开始下载"
                )
            elif "zh" in subtitle["lan"]:
                _LOGGER.info(
                    f"这个字幕为中文字幕，语言代码为：{subtitle['lan']}，中文名称为：{subtitle['lan_doc']}，开始下载"
                )
            else:
                _LOGGER.info(
                    f"这个字幕为外文字幕，语言代码为：{subtitle['lan']}，中文名称为：{subtitle['lan_doc']}，开始下载"
                )
            filename = f"{self.title}.{subtitle['lan']}"
            res = await download_subtitle(
                subtitle["subtitle_url"], self.video_path, filename
            )
            if res is False:
                _LOGGER.info(f"该字幕下载失败，跳过处理")
                continue
            _LOGGER.info(f"该字幕下载完成，保存路径为：{self.video_path}/{filename}")
        _LOGGER.info(f"字幕保存完成：{self.pretty_title}")
        return True

    @handle_error(
        record_error_video=True,
        remove_error_video_folder=True,
        record_video_page=0,
        record_video_bvid=bvid,
        remove_error_video_path=path,
    )
    async def run(self) -> str | bool:
        """执行刮削

        Returns:
            bool: 是否刮削成功
        """
        _LOGGER.info("收到刮削任务，先等我检查一下传入参数是否正确，并准备一些必要的东西")
        task_list = [
            self.download,
            self.scraper,
            self.scraper_people_folder,
            self.save_danmakus,
            self.save_subtitles,
        ]
        if await self.check_args() is NoRetry:
            return NoRetry
        if await self.get_video_info() is NoRetry:
            return NoRetry
        _LOGGER.info("准备工作完成，开始执行刮削任务")
        for func in task_list:
            res = await func()
            if res is NoRetry:
                _LOGGER.error(f"刮削任务失败，但是会重试")
                return NoRetry
            elif res is False:
                _LOGGER.error(f"刮削任务失败，不会重试")
                return False
        _LOGGER.info(f"视频刮削完成：{self.pretty_title}")
        return True


# if __name__ == "__main__":
#     asyncio.run(ProcessNormalVideo("BV1uG4y1C7Q1", video_path="../tests/video_test", scraper_people=True, emby_people_path="../tests/people").run())

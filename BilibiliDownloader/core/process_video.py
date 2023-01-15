"""核心部分，控制视频下载刮削流程"""

import traceback
import shutil

import ffmpeg
import httpx
from aiofiles import open, os
import os as _os
import sys

from bilibili_api import video, user, sync, exceptions, ass
from utils import handle_error, global_value, LOGGER
from . import downloader, nfo_generator

global_value.init()
global_value.set_value("local_path", _os.path.split(_os.path.realpath(__file__))[0])
local_path = global_value.get_value("local_path")
_LOGGER = LOGGER
NoRetry = "NoRetry"


class DownloadError(Exception):
    pass


async def get_video_info(bvid: str = None, video_object: video.Video = None) -> tuple[dict, video.Video] | bool:
    """获取视频信息

    :param bvid: BV号(和video_object二选一)
    :param video_object: 视频对象

    :return: 视频信息，视频对象
    """
    if video_object is None and bvid is None:
        raise ValueError("bvid和video_object不能同时为空")
    try:
        video_object = video.Video(bvid=bvid) if bvid is not None else video_object
        video_info = await video_object.get_info()
        return video_info, video_object
    except exceptions.ResponseCodeException:
        _LOGGER.error(f"视频 {bvid} 不存在，详细报错信息：\n{traceback.format_exc()}")
        return False
    except exceptions.ArgsException:
        _LOGGER.error(f"BV号输入错误，详细报错信息：\n{traceback.format_exc()}")
        return False
    except Exception:
        _LOGGER.error(f"获取视频 {bvid} 信息时发生未知错误，详细报错信息：\n{traceback.format_exc()}")
        return False


async def download_video(video_object: video.Video, dst: str, filename: str, page: int = 0) -> str | bool:
    """下载视频

    :param video_object: 视频对象
    :param dst: 保存路径
    :param filename: 文件名， 不包含后缀
    :param page: 分P序号

    :return: 是否下载成功
    """
    if not await os.path.exists(dst):
        await os.makedirs(dst, exist_ok=True)
    res = await get_video_info(video_object=video_object)
    if res is False:
        _LOGGER.error(f"跳过此视频下载")
        return NoRetry
    video_info, video_object = res
    title = video_info["title"].replace("/", " ")
    pretty_title = " 「" + title + "」 "
    if not await os.path.exists(f"{local_path}/tmp/{title}"):
        await os.makedirs(f"{local_path}/tmp/{title}", exist_ok=True)
    try:
        url = await video_object.get_download_url(page_index=page)
    except exceptions.ResponseCodeException:
        _LOGGER.error(f"视频{pretty_title}不存在，详细报错信息：\n{traceback.format_exc()}")
        return False
    _LOGGER.info(f"该视频存在 {url['accept_description']} 种清晰度，根据你的账号权限，开始选择最高清晰度下载")
    video_url = url["dash"]["video"][0]["baseUrl"]
    audio_url = url["dash"]["audio"][0]["baseUrl"]
    DownloadFunc = downloader.DownloadFunc
    v_path = f"{local_path}/tmp/{title}/video_temp.m4s"
    res, v_size = await DownloadFunc(video_url, v_path).download_with_resume()
    if res:
        _LOGGER.info(f"{pretty_title} m4s视频下载到完成")
    else:
        _LOGGER.error(f"{pretty_title} m4s视频下载失败")
        return False
    a_path = f"{local_path}/tmp/{title}/audio_temp.m4s"
    res, a_size = await DownloadFunc(audio_url, a_path).download_with_resume()
    if res:
        _LOGGER.info(f"{pretty_title} m4s音频下载完成")
    else:
        _LOGGER.error(f"{pretty_title} m4s音频下载失败")
        return False
    if v_size == 0 or a_size == 0 or v_size == 202 or a_size == 202:
        _LOGGER.error(f"{pretty_title} 下载资源大小不正确，放弃本次下载，稍后重试")
        return False
    in_video = ffmpeg.input(v_path)
    in_audio = ffmpeg.input(a_path)
    ffmpeg.output(
        in_video,
        in_audio,
        f"{dst}/{filename}.mp4",
        vcodec="copy",
        acodec="copy",
    ).run(overwrite_output=True)
    await os.remove(v_path)
    await os.remove(a_path)
    await os.removedirs(f"{local_path}/tmp/{title}")
    _LOGGER.info(
        f"视频音频下载完成，已混流为mp4文件，保存路径为：{dst}/{filename}.mp4"
    )
    return True


async def download_video_cover(video_info: dict, dst: str, filename: str) -> bool:
    """下载视频封面

    :param video_info: 视频信息
    :param dst: 保存路径
    :param filename: 文件名， 不包含后缀

    :return: 是否下载成功
    """
    if not await os.path.exists(dst):
        await os.makedirs(dst, exist_ok=True)
    download_url = video_info["pic"]
    title = video_info["title"].replace("/", " ")
    pretty_title = " 「" + title + "」 "
    DownloadFunc = downloader.DownloadFunc
    res = await DownloadFunc(download_url, f"{dst}/{filename}.jpg").download_cover()
    if res:
        _LOGGER.info(f"{pretty_title} 封面下载完成，保存路径为：{dst}/{filename}.jpg")
        return True
    else:
        _LOGGER.error(f"{pretty_title} 封面下载失败")
        return False


async def download_people_image(video_info: dict, dst: str, filename: str, people_name: str) -> str | bool:
    """下载用户头像

    :param video_info: 视频信息
    :param dst: 保存路径
    :param filename: 文件名， 不包含后缀
    :param people_name: 要下载头像的up主名字

    :return: 是否下载成功
    """
    if not await os.path.exists(dst):
        await os.makedirs(dst, exist_ok=True)
    DownloadFunc = downloader.DownloadFunc
    if "staff" in video_info:
        for staff in video_info["staff"]:
            if staff["name"] == people_name:
                download_url = staff["face"]
                break
    elif video_info["owner"]["name"] == people_name:
        download_url = video_info["owner"]["face"]
    else:
        _LOGGER.error(f"视频信息中不存在 {people_name} 的头像信息")
        return NoRetry
    res = await DownloadFunc(download_url, f"{dst}/{filename}.jpg").download_cover()
    if res:
        _LOGGER.info(f"up主头像下载完成，保存路径为：{dst}/{filename}.jpg")
        return True
    else:
        _LOGGER.error(f"up主头像下载失败")
        return False


class ProcessNormalVideo:
    def __init__(self, bvid: str, video_path: str, scraper_people: bool, emby_people_path: str = None):
        """单视频下载刮削流程

        Args:
            bvid (str): 视频bvid
            video_path (str): 本视频及数据的保存路径
            scraper_people (bool): 是否刮削up主
            emby_people_path (str, optional): up主文件夹路径
        """
        self.pretty_title = None
        self.title = None
        self.video_object = None
        self.video_info = None
        self.bvid = bvid
        self.video_path = video_path
        self.scraper_people = scraper_people
        self.emby_people_path = emby_people_path

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
        res = await download_video(
            video_object=self.video_object,
            dst=self.video_path,
            filename=self.video_info["title"],
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

    async def run(self) -> str | bool:
        """执行刮削

        Returns:
            bool: 是否刮削成功
        """
        _LOGGER.info("收到刮削任务，先等我检查一下传入参数是否正确，并准备一些必要的东西")
        func_list = [
            self.download,
            self.scraper,
            self.scraper_people_folder,
        ]
        if await self.check_args() is NoRetry:
            return NoRetry
        if await self.get_video_info() is NoRetry:
            return NoRetry
        for func in func_list:
            res = await func()
            if res is NoRetry:
                _LOGGER.error(f"刮削任务失败，但是会重试")
                return NoRetry
            elif res is False:
                _LOGGER.error(f"刮削任务失败，不会重试")
                return False
        _LOGGER.info(f"开始刮削视频：{self.pretty_title}")
        # asyncio.get_event_loop()
        # tasks = [
        #     asyncio.create_task(self.download()),
        #     asyncio.create_task(self.scraper()),
        #     asyncio.create_task(self.scraper_people_folder()),
        # ]
        # res = await asyncio.gather(*tasks)
        # if False or NoRetry in res:
        #     return False
        _LOGGER.info(f"视频刮削完成：{self.pretty_title}")
        return True

# if __name__ == "__main__":
#     asyncio.run(ProcessNormalVideo("BV1uG4y1C7Q1", video_path="../tests/video_test", scraper_people=True, emby_people_path="../tests/people").run())

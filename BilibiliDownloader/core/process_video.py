"""核心部分，控制视频下载刮削流程"""

import os
import re
import asyncio
import logging
import traceback
import httpx
import aiofiles

from bilibili_api import video, user, sync, exceptions, ass
from utils import handle_error, global_value, LOGGER
from . import downloader

local_path = global_value.get_value("local_path")
_LOGGER = LOGGER

class PublicFunction:

    @staticmethod
    def get_video_info(bvid: str) -> tuple[dict, video.Video] | bool:
        """获取视频信息

        Args:
            bvid (str): 视频bvid

        Returns:
            dict: 视频信息
            video.Video: 视频对象
            bool: 视频不存在
        """
        try:
            video_object = video.Video(bvid=bvid)
            video_info = sync(video_object.get_info())
            return video_info, video_object
        except exceptions.ResponseCodeException:
            logging.error(f"视频{bvid}不存在，详细报错信息：\n{traceback.format_exc()}")
            return False
        except exceptions.ArgsException:
            logging.error(f"BV号输入错误，详细报错信息：\n{traceback.format_exc()}")
            return False
        except Exception:
            logging.error(f"获取视频{bvid}信息时发生未知错误，详细报错信息：\n{traceback.format_exc()}")
            return False

    @staticmethod
    async def download_video(video_object: video.Video, dst: str, page: int=0) -> bool and str:
        """下载视频

        Args:
            video_object (video.Video): 视频对象
            dst (str): 视频保存路径, 不包含文件名
            page (int, optional): 视频分p. Defaults to 0.

        Returns:
            bool: 下载是否成功
            str: 视频文件名
        """
        if os.path.exists()
        title = video_object.get_info()["title"]
        pretty_title = "「" + title.replace("/", " ") + "」"
        url = await video_object.get_download_url(page=page)
        #TODO log一下用户可选的视频分辨率，然后选择最高的
        video_url = url["dash"]["video"][0]["baseUrl"]
        audio_url = url["dash"]["audio"][0]["baseUrl"]
        DownloadFunc = downloader.DownloadFunc
        res, v_size = await DownloadFunc(video_url, dst).download_with_resume()
        if res:
            _LOGGER.info(f"{pretty_title} 视频下载完成")
        else:
            raise DownloadError(f"{pretty_title} 视频下载失败")
        path = f"{self.video_path}/audio_temp.m4s"
        res, a_size = await DownloadFunc(audio_url, path).download_with_resume()
        if res:
            _LOGGER.info(f"{pretty_title} 音频下载完成")
        else:
            raise DownloadError(f"{pretty_title} 视频下载失败")
        if v_size == 0 or a_size == 0 or v_size == 202 or a_size == 202:
            _LOGGER.warning(f"{pretty_title} 下载资源大小不正确，放弃本次下载，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            return
        in_video = ffmpeg.input(f"{self.video_path}/video_temp.m4s")
        in_audio = ffmpeg.input(f"{self.video_path}/audio_temp.m4s")
        ffmpeg.output(
            in_video,
            in_audio,
            f'{self.video_path}/{self.video_info["title"]} ({raw_year}).mp4',
            vcodec="copy",
            acodec="copy",
        ).run(overwrite_output=True)
        os.remove(f"{self.video_path}/video_temp.m4s")
        os.remove(f"{self.video_path}/audio_temp.m4s")
        _LOGGER.info(
            f"视频音频下载完成，已混流为mp4文件，文件名： 「{self.video_info['title']} ({raw_year}).mp4」"
        )


        

class ProcessNormalVideo:
    def __init__(self, bvid: str, media_path: str, scraper_people: bool, emby_people_path: str=None):
        """单视频下载刮削流程

        Args:
            bvid (str): 视频bvid
            media_path (str): 媒体文件夹路径
            scraper_people (bool): 是否刮削up主
            emby_people_path (str, optional): up主文件夹路径
        """
        self.bvid = bvid
        self.media_path = media_path
        self.scraper_people = scraper_people
        self.emby_people_path = emby_people_path

        if scraper_people and emby_people_path is None:
            raise ValueError("开启了人物刮削，但未指定emby人物文件夹路径")
        elif os.path.exists(emby_people_path) is False:
            raise ValueError("emby人物文件夹不存在，请检查是否将emby人物文件夹挂载到了mr容器中，并检查是否输入错误")

    async def get_video_info(self):
        """获取视频信息"""
        
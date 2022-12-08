"""
本文件为这个屎山代码又增添了一层屎山，不过这个屎山是为了解决B站的多p视频下载问题而存在的，所以我觉得还是可以的
代码写得像屎一样
你不堪一顾
混乱无序
谁也看不懂
你自己都搞不定
毫无逻辑
如同烂泥打滚
你永远不会成功
永远无法超越
像屎一样的代码
永远不值一提
"""
import asyncio
import os
import random
import shutil
import time
import traceback

import ffmpeg
import loguru
from bilibili_api import video
from lxml import etree
import logging

from main import *
from main import _LOGGER

credential = None
path = ""
root = ""


class ProcessPagesVideo(BilibiliOneVideoProcess):
    def __init__(self, video_id, if_get_character, emby_persons_path, media_path):
        super().__init__(video_id, media_path, emby_persons_path, if_get_character)
        self.credential = None
        self.pages_num = None
        self.video_info = None
        self.video_id = video_id
        self.if_get_character = if_get_character
        self.emby_persons_path = emby_persons_path
        self.media_path = media_path

    async def _get_video_info(self):
        self.v = video.Video(bvid=self.video_id)
        self.video_info = await self.v.get_info()
        self.pages_num = len(await self.v.get_pages())

    async def _download_video(self, page):
        try:
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            if not os.path.exists(f"{local_path}/{self.video_info['title']} ({raw_year})/Season 1"):
                os.makedirs(f"{local_path}/{self.video_info['title']} ({raw_year})/Season 1", exist_ok=True)
            _LOGGER.info(f"收到视频 P{page + 1} 下载请求，开始下载到临时文件夹")
            path = f'{local_path}/{self.video_info["title"]} ({raw_year})/Season 1/video_temp_{page}.m4s'
            url = await self.v.get_download_url(page_index=page)
            video_url = url["dash"]["video"][0]['baseUrl']
            audio_url = url["dash"]["audio"][0]['baseUrl']
            res = await DownloadFunc(video_url, path).download_with_resume()
            if res:
                _LOGGER.info(f"视频 P{page + 1} 下载完成")
            else:
                Utils.write_error_video(self.video_info)
                Utils.delete_video_folder(self.video_info)
                return None
            path = f'{local_path}/{self.video_info["title"]} ({raw_year})/Season 1/audio_temp_{page}.m4s'
            res = await DownloadFunc(audio_url, path).download_with_resume()
            if res:
                _LOGGER.info(f"音频 P{page + 1} 下载完成")
            else:
                Utils.write_error_video(self.video_info)
                Utils.delete_video_folder(self.video_info)
                return None
            in_video = ffmpeg.input(
                f'{local_path}/{self.video_info["title"]} ({raw_year})/Season 1/video_temp_{page}.m4s')
            in_audio = ffmpeg.input(
                f'{local_path}/{self.video_info["title"]} ({raw_year})/Season 1/audio_temp_{page}.m4s')
            ffmpeg.output(in_video, in_audio,
                          f'{local_path}/{self.video_info["title"]} ({raw_year})/Season 1/{self.video_info["title"]} S01E{page + 1:02d}.mp4',
                          vcodec='copy', acodec='copy', loglevel="error").run(overwrite_output=True)
            os.remove(f"{local_path}/{self.video_info['title']} ({raw_year})/Season 1/video_temp_{page}.m4s")
            os.remove(f"{local_path}/{self.video_info['title']} ({raw_year})/Season 1/audio_temp_{page}.m4s")
            _LOGGER.info(f'视频音频下载完成，已混流为mp4文件，文件名：{self.video_info["title"]} S01E{page + 1:02d}.mp4')
        except Exception:
            _LOGGER.error(f"视频 {self.video_info['title']} 下载失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _download_video_cover(self):
        """下载视频封面"""
        if Utils.read_error_video(self.video_info):
            return
        _LOGGER.info("开始下载视频封面")
        raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
        path = f'{local_path}/{self.video_info["title"]} ({raw_year})/poster.jpg'
        res = await DownloadFunc(self.video_info["pic"], path).download_cover()
        if res:
            _LOGGER.info("视频封面下载完成")
        else:
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            return None

    async def _gen_video_nfo(self, page, media_type):
        """ 生成视频nfo文件

        :param page: 第几P
        :param media_type: nfo类型，有tvshow和episodedetails两种
        """
        global root, path
        try:
            if Utils.read_error_video(self.video_info):
                return
            _LOGGER.info("开始生成nfo文件")
            video_info = self.video_info
            if media_type == 1:
                root = etree.Element("tvshow")
            elif media_type == 2:
                root = etree.Element("episodedetails")
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            title = etree.SubElement(root, "title")
            title.text = video_info["title"]
            plot = etree.SubElement(root, "plot")
            plot.text = video_info["desc"]
            year = etree.SubElement(root, "year")
            year.text = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            premiered = etree.SubElement(root, "premiered")
            premiered.text = time.strftime("%Y-%m-%d", time.localtime(video_info["pubdate"]))
            studio = etree.SubElement(root, "studio")
            studio.text = video_info["owner"]["name"]
            id = etree.SubElement(root, "id")
            id.text = video_info["bvid"]
            genre = etree.SubElement(root, "genre")
            genre.text = video_info["tname"]
            runtime = etree.SubElement(root, "runtime")
            runtime.text = str(video_info["duration"] // 60)
            try:
                for character in video_info["staff"]:
                    actor = etree.SubElement(root, "actor")
                    name = etree.SubElement(actor, "name")
                    name.text = character["name"]
                    role = etree.SubElement(actor, "role")
                    role.text = character["title"]
                    mid = etree.SubElement(actor, "bilibili_id")
                    mid.text = str(character["mid"])
            except KeyError:
                actor = etree.SubElement(root, "actor")
                name = etree.SubElement(actor, "name")
                name.text = video_info["owner"]["name"]
                type = etree.SubElement(actor, "type")
                type.text = "UP主"
                mid = etree.SubElement(actor, "bilibili_id")
                mid.text = str(video_info["owner"]["mid"])
            tree = etree.ElementTree(root)
            if media_type == 1:
                path = f"{local_path}/{self.video_info['title']} ({raw_year})/tvshow.nfo"
            elif media_type == 2:
                path = f"{local_path}/{self.video_info['title']} ({raw_year})/Season 1/{self.video_info['title']} S01E{page:02d}.nfo"
            tree.write(path, encoding="utf-8", pretty_print=True, xml_declaration=True)
            _LOGGER.info("视频nfo文件生成完成")
        except Exception as e:
            _LOGGER.error(f"nfo生成失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _get_screenshot(self, page):
        """获取视频截图"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            _LOGGER.info("开始给视频截图")
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            path = f'{local_path}/{self.video_info["title"]} ({raw_year})/Season 1/{self.video_info["title"]} S01E{page + 1:02d}.mp4'
            input_video = ffmpeg.input(path)
            timestamp = 1
            screenshot = input_video.filter('select', 'eq(t,{})'.format(timestamp)).output(
                f'{local_path}/{self.video_info["title"]} ({raw_year})/Season 1/{self.video_info["title"]} S01E{page + 1:02d}-thumb.jpg',
                loglevel="error", vframes=1)
            ffmpeg.run(screenshot)
            _LOGGER.info("视频截图完成")
        except Exception as e:
            _LOGGER.error(f"视频截图失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def process(self):
        """视频处理"""
        if not os.path.exists(f"{local_path}/error_video.txt"):
            with open(f"{local_path}/error_video.txt", "w") as f:
                f.write("该文件用于记录下载失败的视频id，以便下次重试，请勿删除\n")
        try:
            await self._get_video_info()
        except Exception:
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"获取视频信息失败，请检查提交的bv号是否正确")
            _LOGGER.error(tracebacklog)
            return
        if Utils.read_error_video(self.video_info):
            return
        for page in range(self.pages_num):
            await self._download_video(page)
            await self._gen_video_nfo(page + 1, 2)
            await self._get_screenshot(page)
        await self._gen_video_nfo(0, 1)
        await self._download_video_cover()
        await super()._get_video_info()
        if self.if_get_character:
            await super()._gen_character_nfo()
            await super()._download_character_folder()
            await super()._move_character_folder()
        await super()._move_video_folder()
        if Utils.read_error_video(self.video_info):
            return
        _LOGGER.info(f"多P视频 {self.video_info['title']} 处理完成")
        Notify(self.video_info).send_all_way()


if __name__ == '__main__':
    asyncio.run(ProcessPagesVideo(video_id="BV1vK4y1p7F5",
                                  emby_persons_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby",
                                  if_get_character=True,
                                  media_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby").process())

"""
bilibili 下载
"""
import asyncio
import logging
import os
import shutil
import time

import ffmpeg
import httpx
import pypinyin
from bilibili_api import video, Credential, HEADERS
from lxml import etree

from .constant import SESSDATA, BILI_JCT, BUVID3

_LOGGER = logging.getLogger(__name__)


class ProcessOneVideo:
    """下载视频、封面、up主头像，生成视频和up主nfo文件"""

    def __init__(self, video_id: str, emby_persons_path: str = None, if_get_character: bool = True,
                 media_path: str = None):
        self.media_path = media_path
        self.if_get_character = if_get_character
        self.emby_persons_path = emby_persons_path
        self.video_id = video_id
        self.credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
        self.video_info = None

    async def _get_video_info(self):
        """获取视频信息"""
        v = video.Video(bvid=self.video_id, credential=self.credential)
        self.video_info = await v.get_info()

    async def _download_video(self):
        """下载视频"""
        v = video.Video(bvid=self.video_id, credential=self.credential)
        raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
        if not os.path.exists(f"{self.video_info['title']} ({raw_year})"):
            os.makedirs(f"{self.video_info['title']} ({raw_year})", exist_ok=True)
        url = await v.get_download_url(0)
        video_url = url["dash"]["video"][0]['baseUrl']
        audio_url = url["dash"]["audio"][0]['baseUrl']
        _LOGGER.info(f"视频地址：{video_url}，音频地址：{audio_url}，开始下载")
        # 显示下载进度

        async with httpx.AsyncClient(headers=HEADERS) as sess:
            resp = await sess.get(video_url)
            length = resp.headers.get('content-length')
            with open(f'{self.video_info["title"]} ({raw_year})/video_temp.m4s', 'wb') as f:
                for chunk in resp.iter_bytes(1024):
                    if not chunk:
                        break
                    f.write(chunk)
            resp = await sess.get(audio_url)
            with open(f'{self.video_info["title"]} ({raw_year})/audio_temp.m4s', 'wb') as f:
                for chunk in resp.iter_bytes(1024):
                    if not chunk:
                        break
                    f.write(chunk)
            in_video = ffmpeg.input(f'{self.video_info["title"]} ({raw_year})/video_temp.m4s')
            in_audio = ffmpeg.input(f'{self.video_info["title"]} ({raw_year})/audio_temp.m4s')
            ffmpeg.output(in_video, in_audio,
                          f'{self.video_info["title"]} ({raw_year})/{self.video_info["title"]} ({raw_year}).mp4',
                          vcodec='copy', acodec='copy', loglevel="quiet").run(overwrite_output=True)
            os.remove(f"{self.video_info['title']} ({raw_year})/video_temp.m4s")
            os.remove(f"{self.video_info['title']} ({raw_year})/audio_temp.m4s")
            _LOGGER.info(f"视频音频下载完成，已混流为{self.video_info['title']} ({raw_year}).mp4")

    async def _download_video_cover(self):
        """下载视频封面"""
        _LOGGER.info("开始下载视频封面")
        async with httpx.AsyncClient(headers=HEADERS) as sess:
            resp = await sess.get(self.video_info["pic"])
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            with open(f'{self.video_info["title"]} ({raw_year})/poster.jpg', 'wb') as f:
                f.write(resp.content)
            _LOGGER.info("视频封面下载完成")

    async def _gen_video_nfo(self):
        """生成视频nfo文件"""
        _LOGGER.info("开始生成视频nfo文件")
        video_info = self.video_info
        raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
        root = etree.Element("video")
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
        runtime.text = str(int(video_info["duration"] / 60))
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
        path = f"{self.video_info['title']} ({raw_year})/{self.video_info['title']} ({raw_year}).nfo"
        tree.write(path, encoding="utf-8", pretty_print=True, xml_declaration=True)
        _LOGGER.info("视频nfo文件生成完成")

    async def _gen_character_nfo(self):
        """生成up主信息"""
        _LOGGER.info("开始生成up主nfo信息")
        video_info = self.video_info
        raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
        os.makedirs(f"{self.video_info['title']} ({raw_year})/character", exist_ok=True)
        try:
            for character in video_info["staff"]:
                os.makedirs(f"{self.video_info['title']} ({raw_year})/character/{character['name']}", exist_ok=True)
                root = etree.Element("person")
                title = etree.SubElement(root, "title")
                title.text = character["name"]
                sorttitle = etree.SubElement(root, "sorttitle")
                sorttitle.text = ''.join(pypinyin.lazy_pinyin(character["name"], style=pypinyin.Style.FIRST_LETTER))
                mid = etree.SubElement(root, "bilibili_id")
                mid.text = str(character["mid"])
                type = etree.SubElement(root, 'uniqueid', type="bilibili_id")
                type.text = str(character["mid"])
                tree = etree.ElementTree(root)
                path = f"{self.video_info['title']} ({raw_year})/character/{character['name']}/person.nfo"
                tree.write(str(path), encoding="utf-8", pretty_print=True, xml_declaration=True)
                _LOGGER.info(f"up主{character['name']}信息生成完成")
        except KeyError:
            os.makedirs(f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
                        exist_ok=True)
            root = etree.Element("person")
            title = etree.SubElement(root, "title")
            title.text = video_info["owner"]["name"]
            sorttitle = etree.SubElement(root, "sorttitle")
            sorttitle.text = ''.join(
                pypinyin.lazy_pinyin(video_info["owner"]["name"], style=pypinyin.Style.FIRST_LETTER))
            mid = etree.SubElement(root, "bilibili_id")
            mid.text = str(video_info["owner"]["mid"])
            type = etree.SubElement(root, 'uniqueid', type="bilibili_id")
            type.text = str(video_info["owner"]["mid"])
            tree = etree.ElementTree(root)
            path = f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}/person.nfo"
            tree.write(str(path), encoding="utf-8", pretty_print=True, xml_declaration=True)
            _LOGGER.info(f"up主{video_info['owner']['name']}信息生成完成")
        _LOGGER.info("up主nfo信息生成完成")

    async def _download_character_folder(self):
        """下载up主头像"""
        _LOGGER.info("开始下载up主头像")
        video_info = self.video_info
        raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
        try:
            for character in video_info["staff"]:
                _LOGGER.info(f"开始下载up主{character['name']}头像")
                async with httpx.AsyncClient(headers=HEADERS) as sess:
                    resp = await sess.get(character["face"])
                    with open(f'{self.video_info["title"]} ({raw_year})/character/{character["name"]}/folder.jpg',
                              'wb') as f:
                        f.write(resp.content)
        except KeyError:
            _LOGGER.info(f"开始下载up主{video_info['owner']['name']}头像")
            async with httpx.AsyncClient(headers=HEADERS) as sess:
                resp = await sess.get(video_info["owner"]["face"])
                with open(f'{self.video_info["title"]} ({raw_year})/character/{video_info["owner"]["name"]}/folder.jpg',
                          'wb') as f:
                    f.write(resp.content)
        _LOGGER.info("up主头像下载完成")

    async def _move_character_folder(self):
        emby_persons_path = self.emby_persons_path
        video_info = self.video_info
        _LOGGER.info(f"开始移动up主头像到emby文件夹{emby_persons_path}")
        raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
        try:
            for character in video_info["staff"]:
                _LOGGER.info(f"开始移动up主{character['name']}头像")
                if not os.path.exists(f"{emby_persons_path}/{character['name'][0]}"):
                    os.makedirs(f"{emby_persons_path}/{character['name'][0]}", exist_ok=True)
                    shutil.move(f"{self.video_info['title']} ({raw_year})/character/{character['name']}",
                                f"{emby_persons_path}/{character['name'][0]}")
                    _LOGGER.info(
                        f"up主{character['name']}头像从{self.video_info['title']} ({raw_year})/character/{character['name']}移动到{emby_persons_path}/{character['name'][0]}")
                elif not os.path.exists(f"{emby_persons_path}/{character['name'][0]}/{character['name']}"):
                    shutil.move(f"{self.video_info['title']} ({raw_year})/character/{character['name']}",
                                f"{emby_persons_path}/{character['name'][0]}")
                    _LOGGER.info(
                        f"up主{character['name']}头像从{self.video_info['title']} ({raw_year})/character/{character['name']}移动到{emby_persons_path}/{character['name'][0]}")
                else:
                    _LOGGER.info(f"up主{character['name']}数据已存在，跳过")
        except KeyError:
            _LOGGER.info(f"开始移动up主{video_info['owner']['name']}头像")
            if not os.path.exists(f"{emby_persons_path}/{video_info['owner']['name'][0]}"):
                os.makedirs(f"{emby_persons_path}/{video_info['owner']['name'][0]}", exist_ok=True)
                shutil.move(f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
                            f"{emby_persons_path}/{video_info['owner']['name'][0]}")
                _LOGGER.info(
                    f"up主{video_info['owner']['name']}头像从{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}移动到{emby_persons_path}/{video_info['owner']['name'][0]}")
            elif not os.path.exists(
                    f"{emby_persons_path}/{video_info['owner']['name'][0]}/{video_info['owner']['name']}"):
                shutil.move(f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
                            f"{emby_persons_path}/{video_info['owner']['name'][0]}")
                _LOGGER.info(
                    f"up主{video_info['owner']['name']}头像从{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}移动到{emby_persons_path}/{video_info['owner']['name'][0]}")
            else:
                _LOGGER.info(f"up主{video_info['owner']['name']}数据已存在，跳过")
        finally:
            shutil.rmtree(f'{self.video_info["title"]} ({raw_year})/character')
        _LOGGER.info("up主头像移动完成")

    async def _move_video_folder(self):
        emby_videos_path = self.media_path
        video_info = self.video_info
        raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
        _LOGGER.info(f"开始移动视频文件夹到指定媒体文件夹{emby_videos_path}")
        if not os.path.exists(f"{emby_videos_path}/bilibili") and not os.path.exists(
                f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})"):
            _LOGGER.info(f"移动{self.video_info['title']} ({raw_year})到{emby_videos_path}/bilibili")
            os.makedirs(f"{emby_videos_path}/bilibili", exist_ok=True)
            shutil.move(f'{self.video_info["title"]} ({raw_year})', f"{emby_videos_path}/bilibili")
        elif os.path.exists(f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})"):
            _LOGGER.warning(f"{self.video_info['title']} ({raw_year})已存在，覆盖掉")
            shutil.rmtree(f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})")
            shutil.move(f'{self.video_info["title"]} ({raw_year})', f"{emby_videos_path}/bilibili")
        else:
            _LOGGER.info(f"移动{self.video_info['title']} ({raw_year})到{emby_videos_path}/bilibili")
            shutil.move(f'{self.video_info["title"]} ({raw_year})', f"{emby_videos_path}/bilibili")
        _LOGGER.info("视频文件夹移动完成")

    async def process(self):
        """
        从bilibili下载视频、封面、up主头像，生成视频和up主nfo文件
        :param if_get_character: 是否下载up主信息到emby_persons文件夹
        """
        await self._get_video_info()
        await self._download_video()
        await self._download_video_cover()
        await self._gen_video_nfo()
        if self.if_get_character:
            await self._gen_character_nfo()
            await self._download_character_folder()
            await self._move_character_folder()
        await self._move_video_folder()
        _LOGGER.info(f"视频{self.video_info['title']}下载刮削完成")


if __name__ == '__main__':
    list = ['BV1bB4y1c7X4', 'BV19K411m753']
    for i in list:
        asyncio.run(ProcessOneVideo(i, "E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby", True,
                                    media_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby").process())

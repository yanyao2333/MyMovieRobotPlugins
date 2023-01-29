"""根据传来的数据生成nfo"""

from aiofiles import os
import time
from lxml import etree
from enum import Enum

import pypinyin
from ..utils import LOGGER
from ..utils.decorators import handle_error
from copy import deepcopy

_LOGGER = LOGGER


class MediaInfoError(Exception):
    """媒体信息错误"""

    pass


class NfoGenerator:

    def __init__(self, media_info: dict, page: int = 0, uploader_folder_mode: bool = False) -> None:
        """构建nfo元数据，返回xml
        Args:
            media_info (dict): bilibili_api返回的视频info
            page (int, optional): 指定分p视频的p数，0为普通视频 Defaults to 0.
            uploader_folder_mode (int, optional): 是否为up主信息模式
        """
        self.media_info = media_info
        self.page = page
        if uploader_folder_mode is False:
            if not self._validate_media_info():
                raise MediaInfoError(
                    "传入的media_info不合法，可能是被风控了，跳过该视频。详细media_info内容：\n{}".format(
                        self.media_info
                    )
                )
            self.title = self.media_info["title"]
        else:
            self.title = self.media_info["name"]
        _LOGGER.info(media_info)

    def _validate_media_info(self) -> bool:
        """验证传入的media_info是否合法
        Returns:
            bool: 是否合法
        """
        check_key_list = ["title", "pubdate", "desc", "bvid", "duration", "tname"]
        for key in check_key_list:
            if key not in self.media_info:
                return False
        return True

    async def _process_media_info(self) -> dict:
        """给传入的media_info加料
        Returns:
            dict: 加料后的media_info
        """
        _media_info = self.media_info
        meta_data = deepcopy(_media_info)
        meta_data.update(
            release_year=time.strftime("%Y", time.localtime(_media_info["pubdate"]))
        )
        meta_data.update(
            minute_duration=(
                str(_media_info["duration"] // 60)
                if _media_info["duration"] // 60 > 0
                else "1"
            )
        )
        meta_data.update(
            pubdate=time.strftime("%Y-%m-%d", time.localtime(_media_info["pubdate"]))
        )
        return meta_data

    async def gen_movie_nfo(self) -> etree.ElementTree:
        """返回由etree构建的xml元数据
        Returns:
            etree.ElementTree: xml元数据
        """
        _LOGGER.info(f"开始生成 {self.title} 的movie nfo文件")
        _video_info = await self._process_media_info()
        root = etree.Element("video")
        title = etree.SubElement(root, "title")
        title.text = _video_info["title"]
        plot = etree.SubElement(root, "plot")
        plot.text = _video_info["desc"]
        year = etree.SubElement(root, "year")
        year.text = _video_info["release_year"]
        premiered = etree.SubElement(root, "premiered")
        premiered.text = _video_info["pubdate"]
        studio = etree.SubElement(root, "studio")
        studio.text = _video_info["owner"]["name"]
        id = etree.SubElement(root, "id")
        id.text = _video_info["bvid"]
        genre = etree.SubElement(root, "genre")
        genre.text = _video_info["tname"]
        runtime = etree.SubElement(root, "runtime")
        runtime.text = _video_info["minute_duration"]
        try:
            for character in _video_info["staff"]:
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
            name.text = _video_info["owner"]["name"]
            type = etree.SubElement(actor, "type")
            type.text = "UP主"
            mid = etree.SubElement(actor, "bilibili_id")
            mid.text = str(_video_info["owner"]["mid"])
        tree = etree.ElementTree(root)
        _LOGGER.info(f"生成 {self.title} 的movie nfo文件成功")
        return tree

    async def gen_tvshow_nfo(self) -> etree.ElementTree:
        """返回由etree构建的xml元数据
        Returns:
            etree.ElementTree: xml元数据
        """
        _LOGGER.info(f"开始生成 {self.title} 的tvshow nfo文件")
        _video_info = await self._process_media_info()
        root = etree.Element("tvshow")
        title = etree.SubElement(root, "title")
        title.text = _video_info["title"]
        plot = etree.SubElement(root, "plot")
        plot.text = _video_info["desc"]
        year = etree.SubElement(root, "year")
        year.text = _video_info["release_year"]
        premiered = etree.SubElement(root, "premiered")
        premiered.text = _video_info["pubdate"]
        studio = etree.SubElement(root, "studio")
        studio.text = _video_info["owner"]["name"]
        id = etree.SubElement(root, "id")
        id.text = _video_info["bvid"]
        genre = etree.SubElement(root, "genre")
        genre.text = _video_info["tname"]
        try:
            for character in _video_info["staff"]:
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
            name.text = _video_info["owner"]["name"]
            type = etree.SubElement(actor, "type")
            type.text = "UP主"
            mid = etree.SubElement(actor, "bilibili_id")
            mid.text = str(_video_info["owner"]["mid"])
        tree = etree.ElementTree(root)
        _LOGGER.info(f"生成 {self.title} 的tvshow nfo文件成功")
        return tree

    async def gen_episodedetails_nfo(self) -> etree.ElementTree:
        """返回由etree构建的xml元数据
        Returns:
            etree.ElementTree: xml元数据
        """
        _LOGGER.info(f"开始生成 {self.title} 的episodedetails nfo文件")
        _video_info = await self._process_media_info()
        root = etree.Element("episodedetails")
        title = etree.SubElement(root, "title")
        title.text = _video_info["title"]
        plot = etree.SubElement(root, "plot")
        plot.text = _video_info["desc"]
        year = etree.SubElement(root, "year")
        year.text = _video_info["release_year"]
        premiered = etree.SubElement(root, "premiered")
        premiered.text = _video_info["pubdate"]
        studio = etree.SubElement(root, "studio")
        studio.text = _video_info["owner"]["name"]
        id = etree.SubElement(root, "id")
        id.text = _video_info["bvid"]
        genre = etree.SubElement(root, "genre")
        genre.text = _video_info["tname"]
        runtime = etree.SubElement(root, "runtime")
        runtime.text = _video_info["minute_duration"]
        season = etree.SubElement(root, "season")
        season.text = "1"
        episode = etree.SubElement(root, "episode")
        episode.text = str(self.page + 1)  # 程序内部页码从0开始，但对外展示从1开始
        try:
            for character in _video_info["staff"]:
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
            name.text = _video_info["owner"]["name"]
            type = etree.SubElement(actor, "type")
            type.text = "UP主"
            mid = etree.SubElement(actor, "bilibili_id")
            mid.text = str(_video_info["owner"]["mid"])
        tree = etree.ElementTree(root)
        _LOGGER.info(f"生成 {self.title} 的episodedetails nfo文件成功")
        return tree

    async def gen_people_nfo(self) -> dict[str, etree.ElementTree]:
        """返回由etree构建的xml元数据
        Returns:
            dict[str, etree.ElementTree]: 所有人物的xml元数据
        """
        _LOGGER.info(f"开始生成 {self.title} 的people nfo文件")
        _video_info = await self._process_media_info()
        tree = {}
        if "staff" in _video_info:
            for character in _video_info["staff"]:
                root = etree.Element("person")
                title = etree.SubElement(root, "title")
                title.text = character["name"]
                sorttitle = etree.SubElement(root, "sorttitle")
                sorttitle.text = "".join(
                    pypinyin.lazy_pinyin(
                        character["name"], style=pypinyin.Style.FIRST_LETTER
                    )
                )
                mid = etree.SubElement(root, "bilibili_id")
                mid.text = str(character["mid"])
                type = etree.SubElement(root, "uniqueid", type="bilibili_id")
                type.text = str(character["mid"])
                tree[character["name"]] = etree.ElementTree(root)
                _LOGGER.info(f"up主 「{character['name']}」 nfo信息生成完成")
        else:
            root = etree.Element("person")
            title = etree.SubElement(root, "title")
            title.text = _video_info["owner"]["name"]
            sorttitle = etree.SubElement(root, "sorttitle")
            sorttitle.text = "".join(
                pypinyin.lazy_pinyin(
                    _video_info["owner"]["name"], style=pypinyin.Style.FIRST_LETTER
                )
            )
            mid = etree.SubElement(root, "bilibili_id")
            mid.text = str(_video_info["owner"]["mid"])
            type = etree.SubElement(root, "uniqueid", type="bilibili_id")
            type.text = str(_video_info["owner"]["mid"])
            tree[_video_info["owner"]["name"]] = etree.ElementTree(root)
            _LOGGER.info(f"up主 「{_video_info['owner']['name']}」 nfo信息生成完成")
            _LOGGER.info(f"{self.title} 的up主nfo信息生成完成")
        return tree

    async def _uploader_info_to_media_info(self):
        """转换api获取到的up主信息为与media_info键相同的字典"""
        _raw_info = deepcopy(self.media_info)
        _uploader_info = {}
        _uploader_info["title"] = _raw_info["name"]
        _uploader_info["desc"] = _raw_info["sign"]
        _uploader_info["bvid"] = str(_raw_info["mid"])
        _uploader_info["release_year"] = time.strftime("%Y", time.localtime(time.time()))
        _uploader_info["pubdate"] = time.strftime("%Y-%m-%d", time.localtime(time.time()))
        _uploader_info["owner"] = {}
        _uploader_info["owner"]["name"] = _raw_info["name"]
        _uploader_info["tname"] = "UP主"
        _uploader_info["owner"]["mid"] = _raw_info["mid"]
        return _uploader_info

    async def gen_tvshow_nfo_by_uploader(self) -> etree.ElementTree:
        """注意，这里传入的media_info实为bilibili_api获取到的uploader_info!!!"""
        _LOGGER.info(f"开始生成 {self.title} 的tvshow nfo文件")
        _video_info = await self._uploader_info_to_media_info()
        root = etree.Element("tvshow")
        title = etree.SubElement(root, "title")
        title.text = _video_info["title"]
        plot = etree.SubElement(root, "plot")
        plot.text = _video_info["desc"]
        year = etree.SubElement(root, "year")
        year.text = _video_info["release_year"]
        premiered = etree.SubElement(root, "premiered")
        premiered.text = _video_info["pubdate"]
        studio = etree.SubElement(root, "studio")
        studio.text = _video_info["owner"]["name"]
        id = etree.SubElement(root, "id")
        id.text = _video_info["bvid"]
        genre = etree.SubElement(root, "genre")
        genre.text = _video_info["tname"]
        actor = etree.SubElement(root, "actor")
        name = etree.SubElement(actor, "name")
        name.text = _video_info["owner"]["name"]
        type = etree.SubElement(actor, "type")
        type.text = "UP主"
        mid = etree.SubElement(actor, "bilibili_id")
        mid.text = str(_video_info["owner"]["mid"])
        tree = etree.ElementTree(root)
        _LOGGER.info(f"生成 {self.title} 的tvshow nfo文件成功")
        return tree

    async def save_nfo(self, tree: etree.ElementTree, nfo_path: str):
        """
        保存nfo文件
        Args:
            tree (etree.ElementTree): 之前构建出来的xml元数据
            nfo_path (str): nfo文件路径（包含文件名及后缀）
        """
        _LOGGER.info(f"开始根据传入的xml信息保存nfo文件")
        if await os.path.exists(nfo_path):
            await os.remove(nfo_path)
        if tree is None:
            raise ValueError("传入的xml信息为空")
        tree.write(nfo_path, encoding="utf-8", xml_declaration=True, pretty_print=True)

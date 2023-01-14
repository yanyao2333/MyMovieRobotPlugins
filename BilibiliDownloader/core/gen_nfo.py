"""根据传来的数据生成nfo"""

import os
import time
from lxml import etree
from enum import Enum

import pypinyin
import utils

_LOGGER = utils.LOGGER

class MediaInfoError(Exception):
    """传入的media_info不合法"""

    pass

class NfoGenerator:
    page = 0
    bvid = ""

    def __init__(self, media_info: dict, page: int = 0) -> None:
        """构建nfo元数据，返回xml

        Args:
            media_info (dict): bilibili_api返回的视频info
            page (int, optional): 指定分p视频的p数，0为普通视频 Defaults to 0.
        """
        self.media_info = media_info
        self.page = page
        NfoGenerator.page = page
        NfoGenerator.bvid = media_info["bvid"]
        if not self._validate_media_info():
            raise MediaInfoError("传入的media_info不合法，可能是被风控了，跳过该视频。详细media_info内容：\n{}".format(self.media_info))
        self.title = self.media_info["title"]
        _LOGGER.info(media_info)

    async def _validate_media_info(self) -> bool:
        """验证传入的media_info是否合法

        Returns:
            bool: 是否合法
        """
        check_key_list = ["title", "pubdate", "desc",  "bvid", "duration", "tname"]
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
        meta_data = _media_info.copy()
        meta_data.update(release_year=time.strftime("%Y", time.localtime(_media_info["pubdate"])))
        meta_data.update(minute_duration=(
                str(_media_info["duration"] // 60)
                if _media_info["duration"] // 60 > 0
                else "1"
            ))
        meta_data.update(pubdate=time.strftime("%Y-%m-%d", time.localtime(_media_info["pubdate"])))
        return meta_data
        
    def _get_id_and_page(self) -> tuple:
        """返回视频id

        Returns:
            str: 视频id
            int: 视频第几p
        """
        return self._video_info["bvid"], self.page

    @utils.handle_error(remove_error_video_folder=True, record_error_video=True, record_video_bvid=bvid, record_video_page=page)
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

    @utils.handle_error(remove_error_video_folder=True, record_error_video=True, record_video_bvid=bvid, record_video_page=page)
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

    @utils.handle_error(remove_error_video_folder=True, record_error_video=True, record_video_bvid=bvid, record_video_page=page)
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

    async def gen_people_nfo(self) -> etree.ElementTree:
        """返回由etree构建的xml元数据

        Returns:
            etree.ElementTree: xml元数据
        """
        _LOGGER.info(f"开始生成 {self.title} 的people nfo文件")
        _video_info = await self._process_media_info()
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
                tree = etree.ElementTree(root)
                path = f"{self.video_path}/character/{character['name']}/person.nfo"
                tree.write(
                    str(path),
                    encoding="utf-8",
                    pretty_print=True,
                    xml_declaration=True,
                )
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
            tree = etree.ElementTree(root)
            _LOGGER.info(f"up主 「{_video_info['owner']['name']}」 nfo信息生成完成")
        _LOGGER.info(f"{self.title} 的up主nfo信息生成完成")

    @utils.handle_error(remove_error_video_folder=True, record_error_video=True, record_video_bvid=bvid, record_video_page=page)
    async def save_nfo(self, tree: etree.ElementTree, nfo_path: str):
        """
        保存nfo文件

        Args:
            tree (etree.ElementTree): 之前构建出来的xml元数据
            nfo_path (str): nfo文件路径（包含文件名及后缀）
        """
        _LOGGER.info(f"开始根据传入的xml信息保存nfo文件")
        if os.path.exists(nfo_path):
            os.remove(nfo_path)
        if tree is None:
            raise ValueError("传入的xml信息为空")
        tree.write(nfo_path, encoding="utf-8", xml_declaration=True, pretty_print=True)

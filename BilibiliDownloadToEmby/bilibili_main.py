"""
主文件 包含工具类和主类
本插件的稳定运行需要祭天一个陈睿，请确保你在使用前完成了这个前置工作 ：）
"""
import asyncio
import loguru
# from moviebotapi import MovieBotServer
import datetime
import json
import logging
import os
import shutil
import sys
import time
import traceback

import ffmpeg
import httpx
import pypinyin
import tenacity
from bilibili_api import video, user, sync, exceptions, ass
from lxml import etree
from moviebotapi import MovieBotServer
from mbot.openapi import mbot_api

# from moviebotapi.core.session import AccessKeySession
# from constant import SERVER_URL, ACCESS_KEY
from . import mr_api, process_pages_video

# import mr_api, process_pages_video

_LOGGER = logging.getLogger(__name__)
# _LOGGER = loguru.logger
# server = MovieBotServer(AccessKeySession(SERVER_URL, ACCESS_KEY))
local_path = os.path.split(os.path.realpath(__file__))[0]
server = mbot_api
credential = None
up_data = {}


class BilibiliOneVideoProcess:
    """bilibili视频下载入库刮削实现类 调用process即可完成单个bv号的下载入库刮削"""

    def __init__(self, video_id: str, media_path: str, emby_persons_path: str = None, if_get_character: bool = False):
        """初始化 Bilibili 类

        :param video_id: 视频id
        :param emby_persons_path: emby人物路径
        :param if_get_character: 是否获取角色信息
        :param media_path: 媒体路径
        """
        self.type = None
        self.media_path = media_path
        self.if_get_character = if_get_character
        self.emby_persons_path = emby_persons_path
        self.video_id = video_id
        self.credential = None
        self.video_info = None
        _LOGGER.info(
            f"收到视频处理请求：bvid： {video_id}，媒体路径： {media_path}， 是否获取角色信息： {if_get_character}， emby人物路径： {emby_persons_path}")

    async def _get_video_info(self, *args, **kwargs):
        """获取视频信息"""
        v = video.Video(bvid=self.video_id, credential=self.credential)
        try:
            self.video_info = await v.get_info()
            self.title = f"「{self.video_info['title']}」"
        except Exception:
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"获取视频信息失败，请检查提交的bv号是否正确！")
            _LOGGER.error(tracebacklog)
            return None

    async def _download_video(self, *args, **kwargs):
        """下载视频"""
        try:
            v = video.Video(bvid=self.video_id, credential=self.credential)
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            if not os.path.exists(f"{local_path}/{self.video_info['title']} ({raw_year})"):
                os.makedirs(f"{local_path}/{self.video_info['title']} ({raw_year})", exist_ok=True)
            _LOGGER.info(f"开始下载 {self.title} 音视频到临时文件夹")
            path = f'{local_path}/{self.video_info["title"]} ({raw_year})/video_temp.m4s'
            url = await v.get_download_url(0)
            video_url = url["dash"]["video"][0]['baseUrl']
            audio_url = url["dash"]["audio"][0]['baseUrl']
            res, v_size = await DownloadFunc(video_url, path).download_with_resume()
            if res:
                _LOGGER.info(f"{self.title} 视频下载完成")
            else:
                Utils.write_error_video(self.video_info)
                Utils.delete_video_folder(self.video_info)
                return None
            path = f'{local_path}/{self.video_info["title"]} ({raw_year})/audio_temp.m4s'
            res, a_size = await DownloadFunc(audio_url, path).download_with_resume()
            if res:
                _LOGGER.info(f"{self.title} 音频下载完成")
            else:
                Utils.write_error_video(self.video_info)
                Utils.delete_video_folder(self.video_info)
                return None
            if v_size == 0 or a_size == 0:
                _LOGGER.error(f"{self.title} 视频或音频大小为0kb，可能是资源失效，不会再次重试")
                Utils.write_error_video(self.video_info)
                Utils.delete_video_folder(self.video_info)
                return None
            in_video = ffmpeg.input(f'{local_path}/{self.video_info["title"]} ({raw_year})/video_temp.m4s')
            in_audio = ffmpeg.input(f'{local_path}/{self.video_info["title"]} ({raw_year})/audio_temp.m4s')
            ffmpeg.output(in_video, in_audio,
                          f'{local_path}/{self.video_info["title"]} ({raw_year})/{self.video_info["title"]} ({raw_year}).mp4',
                          vcodec='copy', acodec='copy').run(overwrite_output=True)
            os.remove(f"{local_path}/{self.video_info['title']} ({raw_year})/video_temp.m4s")
            os.remove(f"{local_path}/{self.video_info['title']} ({raw_year})/audio_temp.m4s")
            _LOGGER.info(f"视频音频下载完成，已混流为mp4文件，文件名： 「{self.video_info['title']} ({raw_year}).mp4」")
        except Exception as e:
            _LOGGER.error(f"{self.title} 下载失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _download_video_cover(self, *args, **kwargs):
        """下载视频封面"""
        if Utils.read_error_video(self.video_info):
            return
        _LOGGER.info(f"开始下载 {self.title}封面")
        raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
        path = f'{local_path}/{self.video_info["title"]} ({raw_year})/poster.jpg'
        res = await DownloadFunc(self.video_info["pic"], path).download_cover()
        if res:
            _LOGGER.info(f"{self.title} 封面下载完成")
        else:
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            return None

    async def _gen_video_nfo(self, *args, **kwargs):
        """生成视频nfo文件"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            _LOGGER.info(f"开始生成 {self.title} 的视频nfo文件")
            video_info = self.video_info
            root = etree.Element("video")
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
            runtime.text = str(self.video_info['duration'] // 60) if self.video_info['duration'] // 60 > 0 else "0"
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
            path = f"{local_path}/{self.video_info['title']} ({raw_year})/{self.video_info['title']} ({raw_year}).nfo"
            tree.write(path, encoding="utf-8", pretty_print=True, xml_declaration=True)
            _LOGGER.info(f"{self.title} 视频nfo文件生成完成")
        except Exception as e:
            _LOGGER.error(f"视频 {self.title} nfo文件生成失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _gen_character_nfo(self, *args, **kwargs):
        """生成up主信息 当前问题：以英文开头的up主生成的nfo无法被emby识别"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            _LOGGER.info(f"开始生成 {self.title} 的up主nfo信息")
            video_info = self.video_info
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            os.makedirs(f"{local_path}/{self.video_info['title']} ({raw_year})/character", exist_ok=True)
            try:
                for character in video_info["staff"]:
                    os.makedirs(f"{local_path}/{self.video_info['title']} ({raw_year})/character/{character['name']}",
                                exist_ok=True)
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
                    path = f"{local_path}/{self.video_info['title']} ({raw_year})/character/{character['name']}/person.nfo"
                    tree.write(str(path), encoding="utf-8", pretty_print=True, xml_declaration=True)
                    _LOGGER.info(f"up主 「{character['name']}」 nfo信息生成完成")
            except KeyError:
                os.makedirs(
                    f"{local_path}/{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
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
                path = f"{local_path}/{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}/person.nfo"
                tree.write(str(path), encoding="utf-8", pretty_print=True, xml_declaration=True)
                _LOGGER.info(f"up主 「{video_info['owner']['name']}」 nfo信息生成完成")
            _LOGGER.info(f"{self.title} 的up主nfo信息生成完成")
        except Exception as e:
            _LOGGER.error(f"{self.title} 的up主nfo信息生成失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _download_character_folder(self, *args, **kwargs):
        """下载up主头像"""
        if Utils.read_error_video(self.video_info):
            return
        _LOGGER.info("开始下载up主头像")
        video_info = self.video_info
        raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
        try:
            for character in video_info["staff"]:
                path = f'{local_path}/{self.video_info["title"]} ({raw_year})/character/{character["name"]}/folder.jpg'
                _LOGGER.info(f"开始下载up主 「{character['name']}」 头像")
                res = await DownloadFunc(character["face"], path).download_cover()
                if res:
                    _LOGGER.info(f"up主 「{character['name']}」 头像下载完成")
            return
        except KeyError:
            _LOGGER.info(f"开始下载up主 「{video_info['owner']['name']}」 头像")
            path = f'{local_path}/{self.video_info["title"]} ({raw_year})/character/{video_info["owner"]["name"]}/folder.jpg'
            res = await DownloadFunc(video_info["owner"]["face"], path).download_cover()
            if res:
                _LOGGER.info(f" 「{video_info['owner']['name']}」 头像下载完成")
            return
        except Exception:
            _LOGGER.error(f"up主头像下载失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _move_character_folder(self, *args, **kwargs):
        """移动up主信息到emby演员文件夹"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            emby_persons_path = self.emby_persons_path
            video_info = self.video_info
            _LOGGER.info(f"开始移动up主头像到emby演员文件夹： 「{emby_persons_path}」")
            _LOGGER.warning("以英文开头的up主名字的头像无法被emby识别，头像显示不出属正常情况，与插件无关")
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            try:
                for character in video_info["staff"]:
                    _LOGGER.info(f"开始移动up主{character['name']}")
                    if not os.path.exists(f"{emby_persons_path}/{character['name'][0]}"):
                        os.makedirs(f"{emby_persons_path}/{character['name'][0]}", exist_ok=True)
                        shutil.move(
                            f"{local_path}/{self.video_info['title']} ({raw_year})/character/{character['name']}",
                            f"{emby_persons_path}/{character['name'][0]}")
                        _LOGGER.info(
                            f"{local_path}/{self.video_info['title']} ({raw_year})/character/{character['name']} -> {emby_persons_path}/{character['name'][0]}")
                    elif not os.path.exists(f"{emby_persons_path}/{character['name'][0]}/{character['name']}"):
                        shutil.move(
                            f"{local_path}/{self.video_info['title']} ({raw_year})/character/{character['name']}",
                            f"{emby_persons_path}/{character['name'][0]}")
                        _LOGGER.info(
                            f"{local_path}/{self.video_info['title']} ({raw_year})/character/{character['name']} -> {emby_persons_path}/{character['name'][0]}")
                    else:
                        _LOGGER.info(f"up主 「{character['name']}」 数据已存在，跳过")
            except KeyError:
                _LOGGER.info(f"开始移动up主 「{video_info['owner']['name']}」")
                if not os.path.exists(f"{emby_persons_path}/{video_info['owner']['name'][0]}"):
                    os.makedirs(f"{emby_persons_path}/{video_info['owner']['name'][0]}", exist_ok=True)
                    shutil.move(
                        f"{local_path}/{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}")
                    _LOGGER.info(
                        f"{local_path}/{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']} -> {emby_persons_path}/{video_info['owner']['name'][0]}")
                elif not os.path.exists(
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}/{video_info['owner']['name']}"):
                    shutil.move(
                        f"{local_path}/{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}")
                    _LOGGER.info(
                        f"{local_path}/{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']} -> {emby_persons_path}/{video_info['owner']['name'][0]}")
                else:
                    _LOGGER.info(f"up主 「{video_info['owner']['name']}」 数据已存在，跳过")
            finally:
                shutil.rmtree(f'{local_path}/{self.video_info["title"]} ({raw_year})/character')
            _LOGGER.info("up主头像移动完成")
        except Exception as e:
            _LOGGER.error(f"{self.title} up主头像移动失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _move_video_folder(self, *args, **kwargs):
        """移动视频文件夹到指定媒体库文件夹"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            emby_videos_path = self.media_path
            video_info = self.video_info
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            _LOGGER.info(f"开始移动视频文件夹到 「{emby_videos_path}」")
            if not os.path.exists(f"{emby_videos_path}/bilibili") and not os.path.exists(
                    f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})"):
                _LOGGER.info(f"{local_path}/{self.video_info['title']} ({raw_year}) -> {emby_videos_path}/bilibili")
                os.makedirs(f"{emby_videos_path}/bilibili", exist_ok=True)
                shutil.move(f'{local_path}/{self.video_info["title"]} ({raw_year})', f"{emby_videos_path}/bilibili")
            elif os.path.exists(f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})"):
                _LOGGER.warning(f"{local_path}/{self.video_info['title']} ({raw_year})已存在，覆盖掉")
                shutil.rmtree(f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})")
                shutil.move(f'{local_path}/{self.video_info["title"]} ({raw_year})', f"{emby_videos_path}/bilibili")
            else:
                _LOGGER.info(f"{local_path}/{self.video_info['title']} ({raw_year}) -> {emby_videos_path}/bilibili")
                shutil.move(f'{local_path}/{self.video_info["title"]} ({raw_year})', f"{emby_videos_path}/bilibili")
            _LOGGER.info("视频文件夹移动完成")
        except Exception as e:
            _LOGGER.error(f"视频 {self.title} 文件夹移动失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _downlod_ass_danmakus(self, *args, **kwargs):
        """下载弹幕"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            _LOGGER.info(f"开始下载视频 {self.title} 弹幕")
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            path = f"{local_path}/{self.video_info['title']} ({raw_year})/{self.video_info['title']} ({raw_year}).danmakus.ass"
            # 这是我个人比较舒服的弹幕样式，可以自行修改
            await ass.make_ass_file_danmakus_protobuf(video.Video(self.video_id), 0, path, fly_time=13, alpha=0.75,
                                                      font_size=20)
            _LOGGER.info(f"视频 {self.title} 弹幕下载完成")
        except exceptions.DanmakuClosedException:
            _LOGGER.warning(f"视频 {self.title} 弹幕下载失败，弹幕已关闭")
        except Exception:
            _LOGGER.error(f"视频 {self.title} 弹幕下载失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def process(self, *args, **kwargs):
        """运行入口函数"""
        if not os.path.exists(f"{local_path}/error_video.txt"):
            with open(f"{local_path}/error_video.txt", "w") as f:
                f.write("")
        if len(await video.Video(bvid=self.video_id, credential=self.credential).get_pages()) != 1:
            _LOGGER.warning(f"视频 「{self.video_id}」 不是单P视频，作为剧集下载到剧集目录")
            await process_pages_video.ProcessPagesVideo(self.video_id, self.if_get_character, self.emby_persons_path,
                                                        self.media_path).process()
            return
        try:
            await self._get_video_info()
        except Exception:
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"获取视频信息失败，请检查提交的bv号是否正确")
            _LOGGER.error(tracebacklog)
            return
        if Utils.read_error_video(self.video_info):
            return
        await self._download_video()
        await self._download_video_cover()
        await self._gen_video_nfo()
        if self.if_get_character:
            await self._gen_character_nfo()
            await self._download_character_folder()
            await self._move_character_folder()
        await self._move_video_folder()
        if Utils.read_error_video(self.video_info):
            return
        _LOGGER.info(f"视频 {self.title} 下载刮削完成，请刷新emby媒体库")
        Notify(self.video_info).send_all_way()


class Utils:
    """工具类"""

    @staticmethod
    def progress_bar(current, total):
        """进度条"""
        rate = current / int(total)
        rate_num = int(rate * 100)
        r = '\r[%s%s]%d%%' % ("=" * rate_num, " " * (100 - rate_num), rate_num,)
        sys.stdout.write(r)
        sys.stdout.flush()

    @staticmethod
    def write_error_video(video_info):
        """记录下载失败的视频"""
        with open(f"{local_path}/error_video.txt", "a") as f:
            f.write(f"{video_info['bvid']}\n")

    @staticmethod
    def read_error_video(video_info):
        """读取下载失败的视频"""
        with open(f"{local_path}/error_video.txt", "r") as f:
            error_video = f.readlines()
            if error_video:
                if f"{video_info['bvid']}\n" in error_video:
                    return True
                else:
                    return False
            else:
                return False

    @staticmethod
    def remove_error_video(video_info):
        """删除下载失败的视频记录"""
        with open(f"{local_path}/error_video.txt", "r") as f:
            lines = f.readlines()
        with open(f"{local_path}/error_video.txt", "w") as f_w:
            for line in lines:
                if video_info["bvid"] not in line:
                    f_w.write(line)

    @staticmethod
    def get_error_video_list():
        """获取下载失败的视频列表"""
        with open(f"{local_path}/error_video.txt", "r") as f:
            lines = f.readlines()
        error_video_list = []
        for line in lines:
            error_video_list.append(line.replace("\n", ""))
        return error_video_list

    @staticmethod
    def if_get_character():
        """获取mr刮削配置，判断是否获取角色信息"""
        api = mr_api.ScraperApi(server.session)
        resp = api.config()
        if resp.get('use_cn_person_name'):
            return True, resp.get('person_nfo_path')
        else:
            return False, None

    @staticmethod
    def get_media_path(type):
        """
        获取mr媒体路径 逻辑：优先选择最靠前的movie/tv类型的路径，如果都没有就返回第一个路径， 反正是下载到bilibili文件夹下，也不会乱

        :param type: 视频是否分P，如果分P则为True，否则为False
        """
        api = mr_api.MediaPath(server.session)
        resp = api.config()
        for i in resp.get('paths'):
            if i.get('type') == 'tv' and type:
                return i.get('target_dir')
            elif i.get('type') == 'movie' and not type:
                return i.get('target_dir')
        return resp.get('paths')[0].get('target_dir')

    @staticmethod
    def delete_video_folder(video_info):
        """删除视频目录"""
        try:
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            shutil.rmtree(f"{local_path}/{video_info['title']} ({raw_year})")
        except Exception as e:
            _LOGGER.error(f"删除视频目录失败")
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    @staticmethod
    def find_and_remove(filename, target_str):
        with open(filename, "r") as f:
            lines = f.readlines()

        with open(filename, "w") as f:
            for line in lines:
                if line.strip() != target_str:
                    f.write(line)

        return


async def retry_video():
    """
    重试下载之前失败的视频 被定时任务调用 每次最多重试2个 防止被封ip
    保佑用户不会被封ip，shark个陈睿来祭天吧
    """
    if not os.path.exists(f"{local_path}/error_video.txt"):
        with open(f"{local_path}/error_video.txt", "w") as f:
            f.write("")
    error_video_list = Utils.get_error_video_list()
    error_video = error_video_list[0] if error_video_list else None
    if error_video is None:
        return
    elif len(error_video) != 12 and error_video[:2] != 'BV':
        Utils.find_and_remove(f"{local_path}/error_video.txt", error_video)
        return
    _LOGGER.info(f"开始重试下载失败的视频 {error_video}")
    # if_people_path, people_path = Utils.if_get_character()
    v = video.Video(bvid=error_video)
    if len(await v.get_pages()) > 1:
        type = True
    else:
        type = False
    # media_path = Utils.get_media_path(type)
    Utils.remove_error_video({"bvid": error_video})
    _LOGGER.info(f"重试下载失败的视频 {error_video} 任务已提交")
    await BilibiliOneVideoProcess(error_video,
                                  emby_persons_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby",
                                  if_get_character=True,
                                  media_path=r"E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby\123").process()


class ListenUploadVideo:
    """查询用户是否发新视频，配合定时任务使用"""

    def __init__(self, uid=123, if_get_character=False, media_path=None, emby_persons_path=None):
        self.uid = uid
        self.if_get_character = if_get_character
        self.media_path = media_path
        self.emby_persons_path = emby_persons_path

    async def listen_no_pages_video_new(self):
        """
        官方没有给查看分p上传时间的接口，遇到分p视频直接ignore，并通知用户自行下载
        so bilibili fuck you!
        """
        _LOGGER.info(f"开始监听用户 {self.uid} 是否上传新视频")
        if not os.path.exists(f"{local_path}/listen_up.json"):
            await self.save_data(f"{local_path}/listen_up.json")
        await self.load_data(f"{local_path}/listen_up.json")
        all_video = await user.User(credential=credential, uid=self.uid).get_videos()
        last_video = all_video['list']['vlist'][0]
        if await self.query_data(self.uid) is not None and self.compare_time(last_video['created'],
                                                                             await self.query_data(self.uid)):
            video_info = await video.Video(bvid=last_video['bvid']).get_info()
            if len(await video.Video(bvid=last_video['bvid']).get_pages()) > 1:
                _LOGGER.info(f"用户{self.uid}发布了分p视频，忽略")
                await self.modify_data(self.uid, last_video['created'], 'update')
                Notify(video_info).send_pages_video_request(self.uid)
                await self.save_data(f"{local_path}/listen_up.json")
                return
            else:
                _LOGGER.info(f"用户 {self.uid} 发布了新视频：{video_info['title']}  开始下载")
                await self.modify_data(self.uid, last_video['created'], 'update')
                await self.save_data(f"{local_path}/listen_up.json")
                await BilibiliOneVideoProcess(last_video['bvid'], if_get_character=self.if_get_character,
                                              media_path=self.media_path,
                                              emby_persons_path=self.emby_persons_path).process()
                return
        elif await self.query_data(self.uid) is None:
            await self.modify_data(self.uid, last_video['created'], 'add')
            await self.save_data(f"{local_path}/listen_up.json")
            return
        elif not self.compare_time(last_video['created'], await self.query_data(self.uid)):
            await self.save_data(f"{local_path}/listen_up.json")
            return

    def compare_time(self, v_timestamp, last_timestamp):
        """比较时间"""
        time1 = datetime.datetime.fromtimestamp(v_timestamp)
        time2 = datetime.datetime.fromtimestamp(last_timestamp)
        if time1 > time2:
            return True
        else:
            return False

    async def modify_data(self, uid, time, mode):
        if mode == "add":
            up_data[uid] = time
        elif mode == "update":
            up_data[uid] = time
        elif mode == "delete":
            up_data.pop(uid, None)

    async def query_data(self, uid):
        if uid in up_data:
            return up_data[uid]
        else:
            return None

    async def save_data(self, file_name):
        with open(file_name, "w") as f:
            # 将 data 字典序列化为 JSON 字符串
            content = json.dumps(up_data)
            # 将 JSON 字符串写入文件
            f.write(content)

    async def load_data(self, file_name):
        with open(file_name, "r") as f:
            # 读取文件内容
            content = f.read()
            # 将 JSON 字符串反序列化为 data 字典
            up_data.update(json.loads(content))


class Notify:
    """在下载整理完成时通知用户（走mr渠道） 只推送给第一个用户"""

    def __init__(self, video_info):
        self.video_info = video_info

    def send_message_by_templ(self):
        """发送模板消息"""
        raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
        title = f"✔️{self.video_info['title']} ({raw_year}) 下载完成"
        pubtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.video_info["pubdate"]))
        desc = self.video_info['desc']
        duration = str(self.video_info['duration'] // 60) if self.video_info['duration'] // 60 > 0 else "0"
        message = f"视频标题：{self.video_info['title']}\n" \
                  f"发布时间：{pubtime}\n" \
                  f"视频时长：{duration}分钟\n" \
                  f"视频标签：{self.video_info['tname']}\n" \
                  f"·····································\n" \
                  f"{desc}"
        link_url = f"https://www.bilibili.com/video/{self.video_info['bvid']}"
        poster_url = self.video_info['pic']
        _LOGGER.info(f"开始发送模板消息")
        server.notify.send_message_by_tmpl(title=title, body=message,
                                           context={"link_url": link_url, "pic_url": poster_url}, to_uid=1)

    def send_sys_message(self):
        """发送系统消息"""
        _LOGGER.info("开始发送系统消息")
        server.notify.send_system_message(title="bilibili下载完成", to_uid=1,
                                          message=f"「{self.video_info['title']}」 下载完成，请刷新媒体库")

    def send_all_way(self):
        """发送所有通知方式"""
        self.send_message_by_templ()
        self.send_sys_message()

    def send_pages_video_request(self, uid):
        """发送分p视频通知"""
        _LOGGER.info("开始发送分p视频通知")
        server.notify.send_system_message(title="bilibili追更提醒", to_uid=1,
                                          message=f"你追更的up主 {self.video_info['owner']['name']} 发布了新的分P视频：{self.video_info['title']}\n由于b站相关api的限制，请自行在视频完结后手动下载")


class DownloadFunc:
    """下载类 用于下载视频和封面"""

    def __init__(self, url, path):
        """
        :param url: 需要下载的url
        :param path: 保存的位置
        """
        self.url = url
        self.path = path
        self.HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"}

    @tenacity.retry(stop=tenacity.stop_after_attempt(6), wait=tenacity.wait_fixed(50),
                    retry=tenacity.retry_if_result(lambda result: result is False))
    async def download_cover(self):
        """
        下载封面用，我不知道怎么回事但是使用下面那个方法下载的封面全是0kb的，就先保留这个
        """
        try:
            _LOGGER.info(f"开始下载url：{self.url}，保存路径：{self.path}")
            async with httpx.AsyncClient(headers=self.HEADERS) as client:
                async with client.stream("GET", self.url) as response:
                    with open(self.path, "wb") as f:
                        async for data in response.aiter_bytes():
                            f.write(data)
        except Exception as e:
            _LOGGER.error(f"下载失败，50秒后重试")
            tracebacklog = traceback.format_exc()
            _LOGGER.error(tracebacklog)
            return False
        else:
            return True

    @tenacity.retry(stop=tenacity.stop_after_attempt(6), wait=tenacity.wait_fixed(50),
                    retry=tenacity.retry_if_result(lambda result: result is False))
    async def download_with_resume(self):
        """这个是我瞎写的包含断点续传功能的下载方法"""
        try:
            async with httpx.AsyncClient() as client:
                _LOGGER.info(f"开始下载url：{self.url}，保存路径：{self.path}")
                response = await client.head(self.url, headers=self.HEADERS)
                file_size = int(response.headers["content-length"])
                try:
                    with open(self.path, "rb") as file:
                        downloaded_size = len(file.read())
                except FileNotFoundError:
                    downloaded_size = 0
                if downloaded_size < file_size:
                    self.HEADERS["range"] = f"bytes={file_size - downloaded_size}"
                    response = await client.get(self.url, headers=self.HEADERS)
                    with open(self.path, "ab") as file:
                        file.write(response.content)
                    with open(self.path, "rb") as file:
                        downloaded_size = len(file.read())
            return True, downloaded_size
        except Exception as e:
            _LOGGER.error(f"下载失败 休息50秒后从失败处重试")
            tracebacklog = traceback.format_exc()
            _LOGGER.error(tracebacklog)
            return False


if __name__ == '__main__':
    start = time.time()
    list = ['BV1A44y1M7jr']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [BilibiliOneVideoProcess(i, emby_persons_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby",
                                     if_get_character=True,
                                     media_path=r"E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby\123").process()
             for i in list]
    loop.run_until_complete(asyncio.wait(tasks))
    end = time.time()
    print('elapsed time = ' + str(end - start))
    # asyncio.run(ListenUploadVideo().listen_new())

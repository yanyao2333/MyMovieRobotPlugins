"""
入口文件 一切的一切从这里开始
"""
import asyncio
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
import pypinyin
from BilibiliDownloader.core import nfo_generator
from bilibili_api import video, user, exceptions, ass
from lxml import etree
from mbot.openapi import mbot_api

from . import process_pages_video
from .mr import mr_api
# from .constant import SERVER_URL, ACCESS_KEY
from .utils import global_value

_LOGGER = logging.getLogger(__name__)
# _LOGGER = loguru.logger
# server = MovieBotServer(AccessKeySession(SERVER_URL, ACCESS_KEY))
local_path = os.path.split(os.path.realpath(__file__))[0]
# if not os.path.exists(f"{local_path}/logs"):
#     os.mkdir(f"{local_path}/logs")
# sys.stderr = open(f"{local_path}/logs/main_stderr.log", "w")
server = mbot_api
credential = global_value.get_value("credential")
_LOGGER.info(f"cookie：{credential}")
up_data = {}
danmaku_config = global_value.get_value("danmaku_config")


class DownloadError(Exception):
    pass


class VideoPathNotSet(Exception):
    pass

class VideoInfo404(Exception):
    pass

def get_config():
    global credential
    credential = global_value.get_value("credential")
    _LOGGER.info(f"重载cookie配置：{credential}")


class BilibiliProcess:
    """bilibili视频下载入库刮削实现类 调用process即可完成单个bv号的下载入库刮削"""

    def __init__(
            self,
            video_id: str,
            media_path: str,
            emby_persons_path: str = None,
            if_get_character: bool = False,
    ):
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
        self.credential = credential
        self.video_info = None
        _LOGGER.info(
            f"收到视频处理请求：bvid： {video_id}，媒体路径： {media_path}， 是否获取角色信息： {if_get_character}， emby人物路径： {emby_persons_path}"
        )

    async def get_video_info(self):
        """获取视频信息"""
        v = video.Video(bvid=self.video_id, credential=self.credential)
        try:
            self.video_info = await v.get_info()
            self.video_info["title"] = self.video_info["title"].replace("/", " ")
            self.title = f"「{self.video_info['title']}」"
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            self.video_path = f"{local_path}/tmp/{self.video_info['title']} ({raw_year})"
        except Exception:
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"获取视频信息失败，请检查提交的bv号是否正确！")
            _LOGGER.error(tracebacklog)

    async def download_video(self):
        """下载视频"""
        try:
            v = video.Video(bvid=self.video_id, credential=self.credential)
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            if not os.path.exists(f"{self.video_path}"):
                os.makedirs(f"{self.video_path}", exist_ok=True)
            _LOGGER.info(f"开始下载 {self.title} 音视频到临时文件夹")
            path = f"{self.video_path}/video_temp.m4s"
            url = await v.get_download_url(0)
            video_url = url["dash"]["video"][0]["baseUrl"]
            audio_url = url["dash"]["audio"][0]["baseUrl"]
            res, v_size = await DownloadFunc(video_url, path).download_with_resume()
            if res:
                _LOGGER.info(f"{self.title} 视频下载完成")
            else:
                raise DownloadError(f"{self.title} 视频下载失败")
            path = f"{self.video_path}/audio_temp.m4s"
            res, a_size = await DownloadFunc(audio_url, path).download_with_resume()
            if res:
                _LOGGER.info(f"{self.title} 音频下载完成")
            else:
                raise DownloadError(f"{self.title} 视频下载失败")
            if v_size == 0 or a_size == 0 or v_size == 202 or a_size == 202:
                _LOGGER.warning(f"{self.title} 下载资源大小不正确，放弃本次下载，稍后重试")
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
        except ffmpeg._run.Error as e:
            _LOGGER.error(f"调用ffmpeg混流mp4失败，程序会稍后重试下载： {e}")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")
        except Exception as e:
            _LOGGER.error(f"{self.title} 下载失败，已记录视频id，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def download_video_cover(self):
        """下载视频封面"""
        if await Utils.read_error_video(self.video_info):
            return
        _LOGGER.info(f"开始下载 {self.title}封面")
        raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
        path = f"{self.video_path}/poster.jpg"
        res = await DownloadFunc(self.video_info["pic"], path).download_cover()
        if res:
            _LOGGER.info(f"{self.title} 封面下载完成")
        else:
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)

    async def gen_video_nfo(self):
        """生成视频nfo文件"""
        try:
            if await Utils.read_error_video(self.video_info):
                return
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            nfo = nfo_generator.NfoGenerator(self.video_info)
            tree = nfo.gen_movie_nfo()
            path = f"{self.video_path}/{self.video_info['title']} ({raw_year}).nfo"
            nfo.save_nfo(tree, path)
            tree.write(path, encoding="utf-8", pretty_print=True, xml_declaration=True)
            _LOGGER.info(f"{self.title} 视频nfo文件生成完成")
        except Exception as e:
            _LOGGER.error(f"视频 {self.title} nfo文件生成失败，已记录视频id，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def gen_character_nfo(self):
        """生成up主信息 当前问题：以英文开头的up主生成的nfo无法被emby识别"""
        try:
            if await Utils.read_error_video(self.video_info):
                return
            _LOGGER.info(f"开始生成 {self.title} 的up主nfo信息")
            video_info = self.video_info
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            os.makedirs(f"{self.video_path}/character", exist_ok=True)
            try:
                for character in video_info["staff"]:
                    os.makedirs(
                        f"{self.video_path}/character/{character['name']}",
                        exist_ok=True,
                    )
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
            except KeyError:
                os.makedirs(
                    f"{self.video_path}/character/{video_info['owner']['name']}",
                    exist_ok=True,
                )
                root = etree.Element("person")
                title = etree.SubElement(root, "title")
                title.text = video_info["owner"]["name"]
                sorttitle = etree.SubElement(root, "sorttitle")
                sorttitle.text = "".join(
                    pypinyin.lazy_pinyin(
                        video_info["owner"]["name"], style=pypinyin.Style.FIRST_LETTER
                    )
                )
                mid = etree.SubElement(root, "bilibili_id")
                mid.text = str(video_info["owner"]["mid"])
                type = etree.SubElement(root, "uniqueid", type="bilibili_id")
                type.text = str(video_info["owner"]["mid"])
                tree = etree.ElementTree(root)
                path = f"{self.video_path}/character/{video_info['owner']['name']}/person.nfo"
                tree.write(
                    str(path), encoding="utf-8", pretty_print=True, xml_declaration=True
                )
                _LOGGER.info(f"up主 「{video_info['owner']['name']}」 nfo信息生成完成")
            _LOGGER.info(f"{self.title} 的up主nfo信息生成完成")
        except Exception as e:
            _LOGGER.error(f"{self.title} 的up主nfo信息生成失败，已记录视频id，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def download_character_folder(self):
        """下载up主头像"""
        if await Utils.read_error_video(self.video_info):
            return
        _LOGGER.info("开始下载up主头像")
        video_info = self.video_info
        raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
        try:
            for character in video_info["staff"]:
                path = f'{self.video_path}/character/{character["name"]}/folder.jpg'
                _LOGGER.info(f"开始下载up主 「{character['name']}」 头像")
                res = await DownloadFunc(character["face"], path).download_cover()
                if res:
                    _LOGGER.info(f"up主 「{character['name']}」 头像下载完成")
            return
        except KeyError:
            _LOGGER.info(f"开始下载up主 「{video_info['owner']['name']}」 头像")
            path = (
                f'{self.video_path}/character/{video_info["owner"]["name"]}/folder.jpg'
            )
            res = await DownloadFunc(video_info["owner"]["face"], path).download_cover()
            if res:
                _LOGGER.info(f" 「{video_info['owner']['name']}」 头像下载完成")
            return
        except Exception:
            _LOGGER.error(f"up主头像下载失败，已记录视频id，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def move_character_folder(self):
        """移动up主信息到emby演员文件夹"""
        try:
            if await Utils.read_error_video(self.video_info):
                return
            emby_persons_path = self.emby_persons_path
            video_info = self.video_info
            _LOGGER.info(f"开始移动up主头像到emby演员文件夹： 「{emby_persons_path}」")
            _LOGGER.warning("以英文开头的up主名字的头像无法被emby识别，头像显示不出属正常情况，与插件无关")
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            try:
                for character in video_info["staff"]:
                    _LOGGER.info(f"开始移动up主{character['name']}")
                    if not os.path.exists(
                            f"{emby_persons_path}/{character['name'][0]}"
                    ):
                        os.makedirs(
                            f"{emby_persons_path}/{character['name'][0]}", exist_ok=True
                        )
                        shutil.move(
                            f"{self.video_path}/character/{character['name']}",
                            f"{emby_persons_path}/{character['name'][0]}",
                        )
                        _LOGGER.info(
                            f"{self.video_path}/character/{character['name']} -> {emby_persons_path}/{character['name'][0]}"
                        )
                    elif not os.path.exists(
                            f"{emby_persons_path}/{character['name'][0]}/{character['name']}"
                    ):
                        shutil.move(
                            f"{self.video_path}/character/{character['name']}",
                            f"{emby_persons_path}/{character['name'][0]}",
                        )
                        _LOGGER.info(
                            f"{self.video_path}/character/{character['name']} -> {emby_persons_path}/{character['name'][0]}"
                        )
                    else:
                        _LOGGER.info(f"up主 「{character['name']}」 数据已存在，跳过")
            except KeyError:
                _LOGGER.info(f"开始移动up主 「{video_info['owner']['name']}」")
                if not os.path.exists(
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}"
                ):
                    os.makedirs(
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}",
                        exist_ok=True,
                    )
                    shutil.move(
                        f"{self.video_path}/character/{video_info['owner']['name']}",
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}",
                    )
                    _LOGGER.info(
                        f"{self.video_path}/character/{video_info['owner']['name']} -> {emby_persons_path}/{video_info['owner']['name'][0]}"
                    )
                elif not os.path.exists(
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}/{video_info['owner']['name']}"
                ):
                    shutil.move(
                        f"{self.video_path}/character/{video_info['owner']['name']}",
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}",
                    )
                    _LOGGER.info(
                        f"{self.video_path}/character/{video_info['owner']['name']} -> {emby_persons_path}/{video_info['owner']['name'][0]}"
                    )
                else:
                    _LOGGER.info(f"up主 「{video_info['owner']['name']}」 数据已存在，跳过")
            finally:
                shutil.rmtree(f"{self.video_path}/character")
            _LOGGER.info("up主头像移动完成")
        except Exception as e:
            _LOGGER.error(f"{self.title} up主头像移动失败，已记录视频id，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def move_video_folder(self):
        """移动视频文件夹到指定媒体库文件夹"""
        try:
            if await Utils.read_error_video(self.video_info):
                return
            emby_videos_path = self.media_path
            video_info = self.video_info
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            _LOGGER.info(f"开始移动视频文件夹到 「{emby_videos_path}」")
            if not os.path.exists(
                    f"{emby_videos_path}/bilibili"
            ) and not os.path.exists(
                f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})"
            ):
                _LOGGER.info(f"{self.video_path} -> {emby_videos_path}/bilibili")
                os.makedirs(f"{emby_videos_path}/bilibili", exist_ok=True)
                shutil.move(f"{self.video_path}", f"{emby_videos_path}/bilibili")
            elif os.path.exists(
                    f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})"
            ):
                _LOGGER.warning(f"{self.video_path}已存在，覆盖掉")
                shutil.rmtree(
                    f"{emby_videos_path}/bilibili/{self.video_info['title']} ({raw_year})"
                )
                shutil.move(f"{self.video_path}", f"{emby_videos_path}/bilibili")
            else:
                _LOGGER.info(f"{self.video_path} -> {emby_videos_path}/bilibili")
                shutil.move(f"{self.video_path}", f"{emby_videos_path}/bilibili")
            _LOGGER.info("视频文件夹移动完成")
        except Exception as e:
            _LOGGER.error(f"视频 {self.title} 文件夹移动失败，已记录视频id，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def downlod_ass_danmakus(self):
        """下载弹幕"""
        try:
            if await Utils.read_error_video(self.video_info):
                return
            _LOGGER.info(f"开始下载视频 {self.title} 弹幕")
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            path = f"{self.video_path}/{self.video_info['title']} ({raw_year}).danmakus.ass"
            danmaku_config = global_value.get_value("danmaku_config")
            _LOGGER.info(f"弹幕样式：{danmaku_config}")
            # 这是我个人比较舒服的弹幕样式，可以自行修改(参照：https://nemo2011.github.io/bilibili-api/#/modules/ass?id=async-def-make_ass_file_danmakus_xml 这个链接上的值修改)
            await ass.make_ass_file_danmakus_protobuf(
                video.Video(self.video_id),
                0,
                path,
                fly_time=danmaku_config["fly_time"],
                alpha=danmaku_config["alpha"],
                font_size=danmaku_config["font_size"],
                static_time=danmaku_config["static_time"],
            )
            _LOGGER.info(f"视频 {self.title} 弹幕下载完成")
            if danmaku_config["number"] is None:
                return
            else:
                _LOGGER.info(f"开始随机删除弹幕到 {danmaku_config['number']} 条")
                await Utils.remove_some_danmaku(path, danmaku_config["number"])
        except exceptions.DanmakuClosedException:
            _LOGGER.warning(f"视频 {self.title} 弹幕下载失败，弹幕已关闭")
        except Exception:
            _LOGGER.error(f"视频 {self.title} 弹幕下载失败，已记录视频id，稍后重试")
            await Utils.write_error_video(self.video_info)
            await Utils.delete_video_folder(self.video_info)
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def process(self):
        """运行入口函数"""
        if not os.path.exists(f"{local_path}/error_video.txt"):
            with open(f"{local_path}/error_video.txt", "w") as f:
                pass
        if not global_value.get_value("cookie_is_valid"):
            _LOGGER.warning("还没登录bilibili账号，无法下载高分辨率视频，终止下载等待登录")
            return False
        if (
                len(
                    await video.Video(
                        bvid=self.video_id, credential=self.credential
                    ).get_pages()
                )
                != 1
        ):
            _LOGGER.warning(f"视频 「{self.video_id}」 不是单P视频，作为剧集下载到剧集目录")
            await process_pages_video.ProcessPagesVideo(
                self.video_id,
                self.if_get_character,
                self.emby_persons_path,
                self.media_path,
            ).process()
            return True
        try:
            await self.get_video_info()
        except Exception:
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"获取视频信息失败，请检查提交的bv号是否正确")
            _LOGGER.error(tracebacklog)
            return True
        if await Utils.read_error_video(self.video_info):
            _LOGGER.info("该视频在失败重试列表，不再下载，等待自动重试")
            return True
        await self.download_video()
        await self.download_video_cover()
        await self.gen_video_nfo()
        await self.downlod_ass_danmakus()
        if self.if_get_character:
            await self.gen_character_nfo()
            await self.download_character_folder()
            await self.move_character_folder()
        await self.move_video_folder()
        if await Utils.read_error_video(self.video_info):
            return True
        _LOGGER.info(f"视频 {self.title} 下载刮削完成，请刷新emby媒体库")
        Notify(self.video_info).send_all_way()
        return True


class Utils:
    """工具类"""

    @staticmethod
    def progress_bar(current, total):
        """进度条"""
        rate = current / int(total)
        rate_num = int(rate * 100)
        r = "\r[%s%s]%d%%" % (
            "=" * rate_num,
            " " * (100 - rate_num),
            rate_num,
        )
        sys.stdout.write(r)
        sys.stdout.flush()

    @staticmethod
    async def write_error_video(video_info, page=0):
        """记录下载失败的视频"""
        with open(f"{local_path}/error_video.txt", "a") as f:
            f.write(f"{video_info['bvid']} P{str(page)}\n")

    @staticmethod
    async def read_error_video(video_info, page=0):
        """读取下载失败的视频"""
        with open(f"{local_path}/error_video.txt", "r") as f:
            error_video = f.readlines()
            if error_video:
                for i in error_video:
                    if f"{video_info['bvid']} P{str(page)}\n" in i:
                        return True
                    else:
                        return False
            else:
                return False

    @staticmethod
    async def remove_error_video(video_info):
        """删除下载失败的视频记录"""
        with open(f"{local_path}/error_video.txt", "r") as f:
            lines = f.readlines()
        with open(f"{local_path}/error_video.txt", "w") as f_w:
            for line in lines:
                if video_info["bvid"] not in line:
                    f_w.write(line)

    @staticmethod
    async def get_error_video_list():
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
        if resp.get("use_cn_person_name"):
            return True, resp.get("person_nfo_path")
        else:
            return False, None

    # TODO: 在插件配置中可以指定媒体库路径
    @staticmethod
    def get_media_path(type):
        """
        现在采用纯用户输入的方式

        :param type: 视频是否分P，如果分P则为True，否则为False
        """
        # api = mr_api.MediaPath(server.session)
        # resp = api.config()
        # for i in resp.get("paths"):
        #     if i.get("target_dir") == "bilibili":
        #         dir = i.get("target_dir")
        #         if dir[-1] == "/":
        #             dir = dir[:-1]
        #         if type:
        #             if os.path.exists(dir + "/pages_video"):
        #                 return f"{dir}/pages_video"
        #             else:
        #                 _LOGGER.info("未找到pages_video文件夹，将创建，请将该文件夹添加到emby媒体库，媒体格式选择为剧集")
        #                 os.makedirs(name=dir + "/pages_video")
        #                 return f"{dir}/pages_video"
        #         else:
        #             return dir
        # for i in resp.get("paths"):
        #     if i.get("type") == "tv" and type:
        #         return i.get("target_dir")
        #     elif i.get("type") == "movie" and not type:
        #         return i.get("target_dir")
        video_dir = global_value.get_value("video_dir")
        part_video_dir = global_value.get_value("part_video_dir")
        if not video_dir:
            _LOGGER.error("未设置视频文件夹路径，请在插件配置中设置，已停止后续下载流程")
            return False
        if not part_video_dir:
            _LOGGER.info("未设置分p视频路径，将使用普通路径")
            part_video_dir = video_dir
        if os.path.exists(video_dir) and os.path.exists(part_video_dir):
            if type:
                return part_video_dir
            else:
                return video_dir
        else:
            _LOGGER.info("未找到bilibili文件夹，开始创建")
            os.makedirs(name=video_dir)
            os.makedirs(name=part_video_dir)
            if type:
                return part_video_dir
            else:
                return video_dir

    @staticmethod
    async def delete_video_folder(video_info, target_str=None):
        """删除视频目录 逻辑：如果提供target_str，删除包含target_str关键字的文件，如果没有提供target_str，则删除视频目录下的所有文件"""
        try:
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            path = f"{local_path}/{video_info['title']} ({raw_year})"
            if target_str:
                filename_list = os.listdir(path)
                for filename in filename_list:
                    if target_str in filename:
                        os.remove(f"{path}/{filename}")
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            shutil.rmtree(f"{local_path}/{video_info['title']} ({raw_year})")
        except Exception as e:
            _LOGGER.error(f"删除视频目录失败")
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    @staticmethod
    async def find_and_remove(filename, target_str):
        with open(filename, "r") as f:
            lines = f.readlines()

        with open(filename, "w") as f:
            for line in lines:
                if line.strip() != target_str:
                    f.write(line)

        return

    @staticmethod
    async def remove_some_danmaku(path, number):
        """更改弹幕条数

        :param path: 弹幕文件路径
        :param number: 保留弹幕条数
        """
        try:
            # 先备份弹幕文件
            shutil.copy(path, f"{path}.bak")
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            danmaku_lines = lines[17:]
            header_lines = lines[:17]
            # _LOGGER.info(f"弹幕条数：{len(danmaku_lines)}，保留弹幕条数：{number}，删除间隔：{remove_interval}")
            lines_to_skip = (len(danmaku_lines) - number) // number
            kept_lines = [
                line for i, line in enumerate(lines) if i % lines_to_skip == 0
            ]
            with open(path, "w") as f:
                for line in header_lines + kept_lines:
                    f.write(line)
        except Exception:
            _LOGGER.error(f"更改弹幕条数失败，开始恢复原弹幕文件")
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")
            shutil.copy(f"{path}.bak", path)


async def retry_video():
    """
    重试下载之前失败的视频 被定时任务调用 每次最多重试1个 防止被封ip
    保佑用户不会被封ip，shark个陈睿来祭天吧
    """
    if not os.path.exists(f"{local_path}/error_video.txt"):
        with open(f"{local_path}/error_video.txt", "w") as f:
            pass
    error_video_list = await Utils.get_error_video_list()
    error_video = error_video_list[0] if error_video_list else None
    bv = error_video.split(" ")[0] if error_video else None
    page = error_video.split(" ")[1][1:] if error_video else None
    if error_video is None:
        return
    elif len(bv) != 12 and bv[:2] != "BV":
        await Utils.find_and_remove(f"{local_path}/error_video.txt", error_video)
        return
    _LOGGER.info(f"开始重试下载失败的视频 {bv}")
    if_people_path, people_path = Utils.if_get_character()
    v = video.Video(bvid=bv, credential=credential)
    _LOGGER.info(f"视频：{bv}，pages：{len(await v.get_pages())}")
    if len(await v.get_pages()) != 1:
        _LOGGER.info("进入多p视频单集重试模式")
        media_path = Utils.get_media_path(True)
        if media_path is False:
            return
        process = process_pages_video.ProcessPagesVideo(
            media_path=media_path,
            if_get_character=if_people_path,
            emby_persons_path=people_path,
            video_id=bv,
        )
        await process.get_video_info()
        await process.retry_one_page(page)
        return
    # if len(await v.get_pages()) > 1:
    #     type = True
    # else:
    #     type = False
    media_path = Utils.get_media_path(False)
    if media_path is False:
        return
    await Utils.remove_error_video({"bvid": error_video})
    _LOGGER.info(f"重试下载失败的视频 {error_video} 任务已提交")
    await BilibiliProcess(
        bv,
        emby_persons_path=people_path,
        if_get_character=if_people_path,
        media_path=media_path,
    ).process()


class ListenUploadVideo:
    """查询用户是否发新视频，配合定时任务使用"""

    def __init__(
            self, uid=123, if_get_character=False, media_path=None, emby_persons_path=None
    ):
        self.uid = uid
        self.if_get_character = if_get_character
        self.media_path = media_path
        self.emby_persons_path = emby_persons_path

    async def listen_no_pages_video_new(self):
        """
        官方没有给查看分p上传时间的接口，遇到分p视频直接ignore，并通知用户自行下载
        so bilibili fuck you!
        """
        # _LOGGER.info(f"开始查询用户 {self.uid} 是否上传新视频")
        if not os.path.exists(f"{local_path}/listen_up.json"):
            await self.save_data(f"{local_path}/listen_up.json")
        elif not await self.verify_json(f"{local_path}/listen_up.json"):
            await self.save_data(f"{local_path}/listen_up.json")
        await self.load_data(f"{local_path}/listen_up.json")
        if not await self.query_data(uid=self.uid):
            await self.modify_data(
                uid=self.uid, time=int(datetime.datetime.now().timestamp()), mode="add"
            )
        all_video = await user.User(credential=credential, uid=self.uid).get_videos(
            ps=50
        )
        video_list = all_video["list"]["vlist"]
        for v in reversed(video_list):
            if await self.query_data(self.uid) is not None and self.compare_time(
                    v["created"], await self.query_data(self.uid)
            ):
                t = await self.query_data(self.uid)
                video_info = await video.Video(bvid=v["bvid"]).get_info()
                if len(await video.Video(bvid=v["bvid"]).get_pages()) > 1:
                    _LOGGER.info(f"用户{self.uid}发布了分p视频，忽略")
                    await self.modify_data(self.uid, v["created"], "update")
                    Notify(video_info).send_pages_video_notify()
                    await self.save_data(f"{local_path}/listen_up.json")
                    continue
                else:
                    _LOGGER.info(f"用户 {self.uid} 发布了新视频：{video_info['title']}  开始下载")
                    res = await BilibiliProcess(
                        v["bvid"],
                        if_get_character=self.if_get_character,
                        media_path=self.media_path,
                        emby_persons_path=self.emby_persons_path,
                    ).process()
                    if res:
                        await self.modify_data(self.uid, v["created"], "update")
                        await self.save_data(f"{local_path}/listen_up.json")
                    continue
            elif await self.query_data(self.uid) is None:
                await self.modify_data(self.uid, v["created"], "add")
                await self.save_data(f"{local_path}/listen_up.json")
                continue
            elif not self.compare_time(v["created"], await self.query_data(self.uid)):
                await self.save_data(f"{local_path}/listen_up.json")
                continue

    def compare_time(self, v_timestamp, last_timestamp):
        """比较时间"""
        time1 = datetime.datetime.fromtimestamp(v_timestamp)
        time2 = datetime.datetime.fromtimestamp(last_timestamp)
        if time1 > time2:
            return True
        else:
            return False

    # 以下为json文件数据处理部分
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
            content = json.dumps(up_data)
            f.write(content)

    async def load_data(self, file_name):
        with open(file_name, "r") as f:
            content = f.read()
            up_data.update(json.loads(content))

    async def verify_json(self, file_name):
        with open(file_name, "r") as f:
            content = f.read()
            try:
                json.loads(content)
                return True
            except json.decoder.JSONDecodeError:
                return False


if __name__ == "__main__":
    start = time.time()
    list = ["BV1A44y1M7jr"]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [
        BilibiliProcess(
            i,
            emby_persons_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby",
            if_get_character=True,
            media_path=r"E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby\123",
        ).process()
        for i in list
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    end = time.time()
    print("elapsed time = " + str(end - start))
    # asyncio.run(ListenUploadVideo().listen_new())

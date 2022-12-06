"""
主文件 包含工具类和主类
"""
import asyncio
import os
import shutil
import sys
import time

import ffmpeg
import httpx
import loguru
import pypinyin
from bilibili_api import video, Credential, HEADERS, exceptions
from lxml import etree
from mbot.openapi import mbot_api

from mr_api import *
from .constant import SESSDATA, BILI_JCT, BUVID3

_LOGGER = loguru.logger
# server = MovieBotServer(AccessKeySession(SERVER_URL, ACCESS_KEY))
server = mbot_api


class BilibiliVideoProcess:
    """bilibili视频下载入库刮削实现类 调用process即可完成单个bv号的下载入库刮削"""

    def __init__(self, video_id: str, media_path: str, emby_persons_path: str = None, if_get_character: bool = False):
        """初始化 Bilibili 类

        :param video_id: 视频id
        :param emby_persons_path: emby人物路径
        :param if_get_character: 是否获取角色信息
        :param media_path: 媒体路径
        """
        self.media_path = media_path
        self.if_get_character = if_get_character
        self.emby_persons_path = emby_persons_path
        self.video_id = video_id
        self.credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
        self.video_info = None
        _LOGGER.info(
            f"开始处理视频 {video_id}，emby人物路径为 {emby_persons_path}， 媒体路径为 {media_path}， 是否获取角色信息为 {if_get_character}")

    async def _get_video_info(self):
        """获取视频信息"""
        v = video.Video(bvid=self.video_id, credential=self.credential)
        self.video_info = await v.get_info()

    async def _download_video(self):
        """下载视频"""
        try:
            v = video.Video(bvid=self.video_id, credential=self.credential)
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            if not os.path.exists(f"{self.video_info['title']} ({raw_year})"):
                os.makedirs(f"{self.video_info['title']} ({raw_year})", exist_ok=True)
            url = await v.get_download_url(0)
            video_url = url["dash"]["video"][0]['baseUrl']
            audio_url = url["dash"]["audio"][0]['baseUrl']
            _LOGGER.info(f"收到视频 {self.video_info['title']} 下载请求，开始下载到临时文件夹")
            async with httpx.AsyncClient(headers=HEADERS) as sess:
                resp = await sess.get(video_url)
                total = resp.headers.get('content-length')
                with open(f'{self.video_info["title"]} ({raw_year})/video_temp.m4s', 'wb') as f:
                    _LOGGER.info(f"开始下载视频")
                    process = 0
                    for chunk in resp.iter_bytes(1024):
                        if not chunk:
                            break
                        process += len(chunk)
                        Utils.progress_bar(process, total)
                        f.write(chunk)
                _LOGGER.info("视频下载完成")
                resp = await sess.get(audio_url)
                total = resp.headers.get('content-length')
                with open(f'{self.video_info["title"]} ({raw_year})/audio_temp.m4s', 'wb') as f:
                    _LOGGER.info(f"开始下载音频")
                    process = 0
                    for chunk in resp.iter_bytes(1024):
                        if not chunk:
                            break
                        process += len(chunk)
                        Utils.progress_bar(process, total)
                        f.write(chunk)
                _LOGGER.info("音频下载完成")
                in_video = ffmpeg.input(f'{self.video_info["title"]} ({raw_year})/video_temp.m4s')
                in_audio = ffmpeg.input(f'{self.video_info["title"]} ({raw_year})/audio_temp.m4s')
                ffmpeg.output(in_video, in_audio,
                              f'{self.video_info["title"]} ({raw_year})/{self.video_info["title"]} ({raw_year}).mp4',
                              vcodec='copy', acodec='copy', loglevel="quiet").run(overwrite_output=True)
                os.remove(f"{self.video_info['title']} ({raw_year})/video_temp.m4s")
                os.remove(f"{self.video_info['title']} ({raw_year})/audio_temp.m4s")
                _LOGGER.info(f"视频音频下载完成，已混流为mp4文件，文件名：{self.video_info['title']} ({raw_year}).mp4")
        except Exception as e:
            _LOGGER.error(f"视频 {self.video_info['title']} 下载失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            _LOGGER.error(f"报错原因：{e}")

    async def _download_video_cover(self):
        """下载视频封面"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            _LOGGER.info("开始下载视频封面")
            async with httpx.AsyncClient(headers=HEADERS) as sess:
                resp = await sess.get(self.video_info["pic"])
                raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
                with open(f'{self.video_info["title"]} ({raw_year})/poster.jpg', 'wb') as f:
                    f.write(resp.content)
                _LOGGER.info("视频封面下载完成")
        except Exception as e:
            _LOGGER.error(f"视频 {self.video_info['title']} 封面下载失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            _LOGGER.error(f"报错原因：{e}")

    async def _gen_video_nfo(self):
        """生成视频nfo文件"""
        try:
            if Utils.read_error_video(self.video_info):
                return
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
        except Exception as e:
            _LOGGER.error(f"视频 {self.video_info['title']} nfo文件生成失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            _LOGGER.error(f"报错原因：{e}")

    async def _gen_character_nfo(self):
        """生成up主信息 当前问题：以英文开头的up主生成的nfo无法被emby识别"""
        try:
            if Utils.read_error_video(self.video_info):
                return
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
        except Exception as e:
            _LOGGER.error(f"up主nfo信息生成失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            _LOGGER.error(f"报错原因：{e}")

    async def _download_character_folder(self):
        """下载up主头像"""
        try:
            if Utils.read_error_video(self.video_info):
                return
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
                    with open(
                            f'{self.video_info["title"]} ({raw_year})/character/{video_info["owner"]["name"]}/folder.jpg',
                            'wb') as f:
                        f.write(resp.content)
            _LOGGER.info("up主头像下载完成")
        except Exception as e:
            _LOGGER.error(f"up主头像下载失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            _LOGGER.error(f"报错原因：{e}")

    async def _move_character_folder(self):
        """移动up主信息到emby演员文件夹"""
        try:
            if Utils.read_error_video(self.video_info):
                return
            emby_persons_path = self.emby_persons_path
            video_info = self.video_info
            _LOGGER.info(f"开始移动up主头像到emby演员文件夹：{emby_persons_path}")
            _LOGGER.warning("以英文开头的up主名字的头像无法被emby识别，头像显示不出属正常情况")
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            try:
                for character in video_info["staff"]:
                    _LOGGER.info(f"开始移动up主{character['name']}")
                    if not os.path.exists(f"{emby_persons_path}/{character['name'][0]}"):
                        os.makedirs(f"{emby_persons_path}/{character['name'][0]}", exist_ok=True)
                        shutil.move(f"{self.video_info['title']} ({raw_year})/character/{character['name']}",
                                    f"{emby_persons_path}/{character['name'][0]}")
                        _LOGGER.info(
                            f"{self.video_info['title']} ({raw_year})/character/{character['name']} -> {emby_persons_path}/{character['name'][0]}")
                    elif not os.path.exists(f"{emby_persons_path}/{character['name'][0]}/{character['name']}"):
                        shutil.move(f"{self.video_info['title']} ({raw_year})/character/{character['name']}",
                                    f"{emby_persons_path}/{character['name'][0]}")
                        _LOGGER.info(
                            f"{self.video_info['title']} ({raw_year})/character/{character['name']} -> {emby_persons_path}/{character['name'][0]}")
                    else:
                        _LOGGER.info(f"up主{character['name']}数据已存在，跳过")
            except KeyError:
                _LOGGER.info(f"开始移动up主{video_info['owner']['name']}")
                if not os.path.exists(f"{emby_persons_path}/{video_info['owner']['name'][0]}"):
                    os.makedirs(f"{emby_persons_path}/{video_info['owner']['name'][0]}", exist_ok=True)
                    shutil.move(f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
                                f"{emby_persons_path}/{video_info['owner']['name'][0]}")
                    _LOGGER.info(
                        f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']} -> {emby_persons_path}/{video_info['owner']['name'][0]}")
                elif not os.path.exists(
                        f"{emby_persons_path}/{video_info['owner']['name'][0]}/{video_info['owner']['name']}"):
                    shutil.move(f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']}",
                                f"{emby_persons_path}/{video_info['owner']['name'][0]}")
                    _LOGGER.info(
                        f"{self.video_info['title']} ({raw_year})/character/{video_info['owner']['name']} -> {emby_persons_path}/{video_info['owner']['name'][0]}")
                else:
                    _LOGGER.info(f"up主{video_info['owner']['name']}数据已存在，跳过")
            finally:
                shutil.rmtree(f'{self.video_info["title"]} ({raw_year})/character')
            _LOGGER.info("up主头像移动完成")
        except Exception as e:
            _LOGGER.error(f"up主头像移动失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            _LOGGER.error(f"报错原因：{e}")

    async def _move_video_folder(self):
        """移动视频文件夹到指定媒体库文件夹"""
        try:
            if Utils.read_error_video(self.video_info):
                return
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
        except Exception as e:
            _LOGGER.error(f"视频文件夹移动失败，已记录视频id，稍后重试")
            Utils.write_error_video(self.video_info)
            Utils.delete_video_folder(self.video_info)
            _LOGGER.error(f"报错原因：{e}")

    async def process(self):
        """运行入口函数"""
        if not os.path.exists("error_video.txt"):
            with open("error_video.txt", "w") as f:
                f.write("该文件用于记录下载失败的视频id，以便下次重试，请勿删除\n")
        try:
            await self._get_video_info()
        except exceptions.ArgsException as e:
            _LOGGER.error(f"参数错误：{e}")
            _LOGGER.error("请重新输入bv号再试！")
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
        _LOGGER.info(f"视频{self.video_info['title']}下载刮削完成，请刷新emby媒体库")


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
        with open("error_video.txt", "a") as f:
            f.write(f"{video_info['bvid']}\n")

    @staticmethod
    def read_error_video(video_info):
        """读取下载失败的视频"""
        with open("error_video.txt", "r") as f:
            error_video = f.readlines()
            print(error_video)
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
        with open("error_video.txt", "r") as f:
            lines = f.readlines()
        with open("error_video.txt", "w") as f_w:
            for line in lines:
                if video_info["bvid"] not in line:
                    f_w.write(line)

    @staticmethod
    def get_error_video_list():
        """获取下载失败的视频列表"""
        with open("error_video.txt", "r") as f:
            lines = f.readlines()
        error_video_list = []
        for line in lines:
            error_video_list.append(line.replace("\n", ""))
        return error_video_list

    @staticmethod
    def if_get_character():
        """获取mr刮削配置，判断是否获取角色信息"""
        api = ScraperApi(server.session)
        resp = api.config()
        if resp.get('use_cn_person_name'):
            return True, resp.get('person_nfo_path')
        else:
            return False, None

    @staticmethod
    def get_media_path():
        """获取mr媒体路径（识别逻辑：优先选择带有bilibili的媒体路径，其次选择最靠前的movie类型的路径），如果都没有就返回第一个路径"""
        api = MediaPath(server.session)
        resp = api.config()
        for i in resp.get('paths'):
            if 'bilibili' in i.get('target_dir') or 'Bilibili' in i.get('target_dir') or 'BILIBILI' in i.get(
                    'target_dir'):
                return i.get('target_dir')
            elif i.get('type') == 'movie':
                return i.get('target_dir')
        return resp.get('paths')[0].get('target_dir')

    @staticmethod
    def delete_video_folder(video_info):
        """删除视频目录"""
        try:
            raw_year = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            shutil.rmtree(f"{video_info['title']} ({raw_year})")
        except Exception as e:
            _LOGGER.error(f"删除视频目录失败，报错原因：{e}")


def retry_video():
    """重试下载之前失败的视频"""
    error_video_list = Utils.get_error_video_list()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    for error_video in error_video_list:
        _LOGGER.info(f"开始重试下载失败的视频{error_video}")
        if_people_path, people_path = Utils.if_get_character()
        media_path = Utils.get_media_path()
        Utils.remove_error_video({"bvid": error_video})
        tasks.append(BilibiliVideoProcess(error_video, if_get_character=if_people_path, media_path=media_path,
                                          emby_persons_path=people_path).process())
        _LOGGER.info(f"重试下载失败的视频 {error_video} 任务已提交")
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()


if __name__ == '__main__':
    start = time.time()
    list = ['BV1wT4y1k7Pw', 'BV15e4y137iM']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [BilibiliVideoProcess(i, emby_persons_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby",
                                  if_get_character=True,
                                  media_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby").process()
             for i in list]
    print(tasks)
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    end = time.time()
    print('elapsed time = ' + str(end - start))

"""
实现多p视频下载到剧集类
"""
import asyncio
import os
import time
import traceback

import ffmpeg
import loguru
from bilibili_api import video, ass, exceptions
from lxml import etree

import bilibili_main
import bilibili_login

_LOGGER = loguru.logger
path = ""
root = ""
# credential = bilibili_login.LoginBilibili().by_scan_qrcode()
credential = None


class ProcessPagesVideo:
    def __init__(self, video_id, if_get_character, emby_persons_path, media_path):
        self.credential = credential
        self.pages_num = None
        self.video_info = None
        self.video_id = video_id
        self.if_get_character = if_get_character
        self.emby_persons_path = emby_persons_path
        self.media_path = media_path

    async def _get_video_info(self):
        try:
            self.v = video.Video(bvid=self.video_id, credential=self.credential)
            self.video_info = await self.v.get_info()
            self.pages_num = len(await self.v.get_pages())
            raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
            self.video_path = (
                f"{bilibili_main.local_path}/{self.video_info['title']} ({raw_year})"
            )
            self.title = f"「{self.video_info['title']}」"
        except Exception as e:
            _LOGGER.error(f"获取视频信息失败，视频id：{self.video_id}")
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")
            return None

    async def _download_video(self, page):
        try:
            if not os.path.exists(f"{self.video_path}/Season 1"):
                os.makedirs(f"{self.video_path}/Season 1", exist_ok=True)
            _LOGGER.info(f"收到视频 P{page + 1} 下载请求，开始下载到临时文件夹")
            path = f"{self.video_path}/Season 1/video_temp_{page + 1}.m4s"
            url = await self.v.get_download_url(page_index=page)
            video_url = url["dash"]["video"][0]["baseUrl"]
            audio_url = url["dash"]["audio"][0]["baseUrl"]
            res = await bilibili_main.DownloadFunc(
                video_url, path
            ).download_with_resume()
            if res:
                _LOGGER.info(f"视频 P{page + 1} 下载完成")
            else:
                bilibili_main.Utils.write_error_video(self.video_info)
                await bilibili_main.Utils.delete_video_folder(
                    self.video_info, target_str=f"S01E{page + 1:02d}"
                )
                return None
            path = f"{self.video_path}/Season 1/audio_temp_{page + 1}.m4s"
            res = await bilibili_main.DownloadFunc(
                audio_url, path
            ).download_with_resume()
            if res:
                _LOGGER.info(f"音频 P{page + 1} 下载完成")
            else:
                bilibili_main.Utils.write_error_video(self.video_info)
                await bilibili_main.Utils.delete_video_folder(
                    self.video_info, target_str=f"S01E{page + 1:02d}"
                )
                return None
            in_video = ffmpeg.input(
                f"{self.video_path}/Season 1/video_temp_{page + 1}.m4s"
            )
            in_audio = ffmpeg.input(
                f"{self.video_path}/Season 1/audio_temp_{page + 1}.m4s"
            )
            ffmpeg.output(
                in_video,
                in_audio,
                f'{self.video_path}/Season 1/{self.video_info["title"]} S01E{page + 1:02d}.mp4',
                vcodec="copy",
                acodec="copy",
                loglevel="error",
            ).run(overwrite_output=True)
            os.remove(f"{self.video_path}/Season 1/video_temp_{page + 1}.m4s")
            os.remove(f"{self.video_path}/Season 1/audio_temp_{page + 1}.m4s")
            _LOGGER.info(
                f'视频音频下载完成，已混流为mp4文件，文件名：{self.video_info["title"]} S01E{page + 1:02d}.mp4'
            )
        except Exception:
            _LOGGER.error(f"视频 {self.video_info['title']} 下载失败，已记录视频id，稍后重试")
            bilibili_main.Utils.write_error_video(self.video_info, page)
            await bilibili_main.Utils.delete_video_folder(
                self.video_info, target_str=f"S01E{page + 1:02d}"
            )
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _download_video_cover(self):
        """下载视频封面"""
        if bilibili_main.Utils.read_error_video(self.video_info):
            return
        _LOGGER.info("开始下载视频封面")
        path = f"{self.video_path}/poster.jpg"
        res = await bilibili_main.DownloadFunc(
            self.video_info["pic"], path
        ).download_cover()
        if res:
            _LOGGER.info("视频封面下载完成")
        else:
            bilibili_main.Utils.write_error_video(self.video_info)
            await bilibili_main.Utils.delete_video_folder(self.video_info)
            return None

    async def _gen_video_nfo(self, page, media_type):
        """生成视频nfo文件

        :param page: 第几P
        :param media_type: nfo类型，有tvshow和episodedetails两种
        """
        global root, path
        try:
            if bilibili_main.Utils.read_error_video(self.video_info, page):
                return
            _LOGGER.info("开始生成nfo文件")
            video_info = self.video_info
            if media_type == 1:
                root = etree.Element("tvshow")
                title = etree.SubElement(root, "title")
                title.text = video_info["title"]
            elif media_type == 2:
                root = etree.Element("episodedetails")
                title = etree.SubElement(root, "title")
                title.text = video_info["pages"][page]["part"]
            plot = etree.SubElement(root, "plot")
            plot.text = video_info["desc"]
            year = etree.SubElement(root, "year")
            year.text = time.strftime("%Y", time.localtime(video_info["pubdate"]))
            premiered = etree.SubElement(root, "premiered")
            premiered.text = time.strftime(
                "%Y-%m-%d", time.localtime(video_info["pubdate"])
            )
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
                path = f"{self.video_path}/tvshow.nfo"
            elif media_type == 2:
                path = f"{self.video_path}/Season 1/{self.video_info['title']} S01E{page + 1:02d}.nfo"
            tree.write(path, encoding="utf-8", pretty_print=True, xml_declaration=True)
            _LOGGER.info("视频nfo文件生成完成")
        except Exception as e:
            _LOGGER.error(f"nfo生成失败，已记录视频id，稍后重试")
            bilibili_main.Utils.write_error_video(self.video_info, page)
            await bilibili_main.Utils.delete_video_folder(
                self.video_info, target_str=f"S01E{page + 1:02d}"
            )
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _get_screenshot(self, page):
        """获取视频截图"""
        try:
            if bilibili_main.Utils.read_error_video(self.video_info, page):
                return
            _LOGGER.info("开始给视频截图")
            path = f'{self.video_path}/Season 1/{self.video_info["title"]} S01E{page + 1:02d}.mp4'
            input_video = ffmpeg.input(path)
            timestamp = 1
            screenshot = input_video.filter(
                "select", "eq(t,{})".format(timestamp)
            ).output(
                f'{self.video_path}/Season 1/{self.video_info["title"]} S01E{page + 1:02d}-thumb.jpg',
                loglevel="error",
                vframes=1,
            )
            ffmpeg.run(screenshot)
            _LOGGER.info("视频截图完成")
        except Exception as e:
            _LOGGER.error(f"视频截图失败，已记录视频id，稍后重试")
            bilibili_main.Utils.write_error_video(self.video_info, page)
            await bilibili_main.Utils.delete_video_folder(
                self.video_info, target_str=f"S01E{page + 1:02d}"
            )
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def retry_one_page(self, page):
        """重试下载某一P"""
        try:
            if bilibili_main.Utils.read_error_video(self.video_info, page):
                return
            _LOGGER.info(f"开始重试第{page + 1}P")
            await self._download_one_page(page)
            _LOGGER.info(f"第{page + 1}P重试完成")
        except Exception as e:
            _LOGGER.error(f"第{page + 1}P重试失败，已记录视频id，稍后重试")
            bilibili_main.Utils.write_error_video(self.video_info, page)
            await bilibili_main.Utils.delete_video_folder(
                self.video_info, target_str=f"S01E{page + 1:02d}"
            )
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def _downlod_ass_danmakus(self, page):
        """下载弹幕"""
        try:
            if bilibili_main.Utils.read_error_video(self.video_info, page):
                return
            _LOGGER.info(f"开始下载视频 {self.title} 弹幕")
            path = f'{self.video_path}/Season 1/{self.video_info["title"]} S01E{page + 1:02d}.danmakus.ass'
            # 这是我个人比较舒服的弹幕样式，可以自行修改
            await ass.make_ass_file_danmakus_protobuf(
                video.Video(self.video_id),
                page,
                path,
                fly_time=13,
                alpha=0.75,
                font_size=20,
            )
            _LOGGER.info(f"视频 {self.title} 弹幕下载完成")
        except exceptions.DanmakuClosedException:
            _LOGGER.warning(f"视频 {self.title} 弹幕下载失败，弹幕已关闭")
        except Exception:
            _LOGGER.error(f"视频 {self.title} 弹幕下载失败，已记录视频id，稍后重试")
            bilibili_main.Utils.write_error_video(self.video_info, page)
            await bilibili_main.Utils.delete_video_folder(
                self.video_info, target_str=f"S01E{page + 1:02d}"
            )
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"报错原因：{tracebacklog}")

    async def process(self):
        """视频处理"""
        if not os.path.exists(f"{bilibili_main.local_path}/error_video.txt"):
            with open(f"{bilibili_main.local_path}/error_video.txt", "w") as f:
                pass
        try:
            await self._get_video_info()
        except Exception:
            tracebacklog = traceback.format_exc()
            _LOGGER.error(f"获取视频信息失败，请检查提交的bv号是否正确")
            _LOGGER.error(tracebacklog)
            return
        if bilibili_main.Utils.read_error_video(self.video_info):
            return
        for page in range(self.pages_num):
            await self._download_video(page)
            await self._gen_video_nfo(page, 2)
            await self._get_screenshot(page)
            await self._downlod_ass_danmakus(page)
        await self._gen_video_nfo(0, 1)
        await self._download_video_cover()
        bProcess = bilibili_main.BilibiliOneVideoProcess(
            self.video_id,
            self.media_path,
            self.emby_persons_path,
            self.if_get_character,
        )
        await bProcess.get_video_info()
        if self.if_get_character:
            await bProcess.gen_character_nfo()
            await bProcess.download_character_folder()
            await bProcess.move_character_folder()
        await bProcess.move_video_folder()
        if bilibili_main.Utils.read_error_video(self.video_info):
            return
        _LOGGER.info(f"多P视频 {self.video_info['title']} 处理完成")
        bilibili_main.Notify(self.video_info).send_all_way()


if __name__ == "__main__":
    asyncio.run(
        ProcessPagesVideo(
            video_id="BV1ZD4y1h78p",
            emby_persons_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby",
            if_get_character=True,
            media_path="E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloadToEmby",
        ).process()
    )

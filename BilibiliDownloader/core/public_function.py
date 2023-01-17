"""我也不知道为什么要单独开一个文件来放这些东西，看起来好看就对了"""

import shutil
import traceback
import httpx
import json

import aiofiles
import ffmpeg
from aiofiles import open, os
import os as _os
from bilibili_api import video, exceptions, ass

from utils import global_value, LOGGER, ccjson2srt
from . import downloader

global_value.init()
global_value.set_value(
    "local_path", _os.path.dirname(_os.path.abspath(__file__)) + "/../"
)
global_value.set_value(
    "danmaku_config",
    {
        "font_size": 25,
        "static_time": 5,
        "fly_time": 7,
        "alpha": 1,
        "number": 10,
    },
)
local_path = global_value.get_value("local_path")
_LOGGER = LOGGER
NoRetry = "NoRetry"


class DownloadError(Exception):
    pass


def _validate_media_info(media_info: dict) -> bool:
    """验证传入的media_info是否合法

    :param media_info: media_info
    :return: 是否合法
    """
    check_key_list = ["title", "pubdate", "desc", "bvid", "duration", "tname"]
    for key in check_key_list:
        if key not in media_info:
            return False
    return True


async def get_video_info(
    bvid: str = None, video_object: video.Video = None
) -> tuple[dict, video.Video] | bool:
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
        if not _validate_media_info(video_info):
            _LOGGER.error(f"视频信息校验失败，中断后续流程，获取到的视频信息为：\n{video_info}")
            return False
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


async def download_video(
    video_object: video.Video, dst: str, filename: str, page: int = 0
) -> str | bool:
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
    _LOGGER.info(f"视频音频下载完成，已混流为mp4文件，保存路径为：{dst}/{filename}.mp4")
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


async def download_people_image(
    video_info: dict, dst: str, filename: str, people_name: str
) -> str | bool:
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


async def remove_some_danmaku(path, number):
    """更改弹幕条数

    :param path: 弹幕文件路径
    :param number: 保留弹幕条数
    """
    try:
        # 先备份弹幕文件
        shutil.copy(path, f"{path}.bak")
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            lines = await f.readlines()
        danmaku_lines = lines[17:]
        header_lines = lines[:17]
        if len(danmaku_lines) < number:
            _LOGGER.info(f"弹幕条数不足 {number} 条，不做处理")
            await os.remove(f"{path}.bak")
            return True
        # _LOGGER.info(f"弹幕条数：{len(danmaku_lines)}，保留弹幕条数：{number}，删除间隔：{remove_interval}")
        lines_to_skip = (len(danmaku_lines) - number) // number
        kept_lines = [line for i, line in enumerate(lines) if i % lines_to_skip == 0]
        async with aiofiles.open(path, "w", encoding="UTF-8") as f:
            for line in header_lines + kept_lines:
                await f.write(line)
        _LOGGER.info(f"弹幕条数已更改为：{number}")
        await os.remove(f"{path}.bak")
        return True
    except Exception:
        _LOGGER.error(f"更改弹幕条数失败，开始恢复原弹幕文件")
        tracebacklog = traceback.format_exc()
        _LOGGER.error(f"报错原因：{tracebacklog}")
        shutil.copy(f"{path}.bak", path)
        if await os.path.exists(path):
            await os.remove(path + ".bak")
            return True
        else:
            return False


async def downlod_ass_danmakus(
    video_object: video.Video, dst: str, filename: str
) -> bool:
    """下载弹幕

    :param video_object: 视频对象
    :param dst: 保存路径
    :param filename: 文件名， 不包含后缀

    :return: 是否下载成功
    """
    try:
        _LOGGER.info(f"开始生成视频弹幕, 保存路径为：{dst}/{filename}.danmaku.ass")
        path = f"{dst}/{filename}.danmaku.ass"
        danmaku_config = global_value.get_value("danmaku_config")
        _LOGGER.info(f"弹幕样式：{danmaku_config}")
        await ass.make_ass_file_danmakus_protobuf(
            video_object,
            0,
            path,
            fly_time=danmaku_config["fly_time"],
            alpha=danmaku_config["alpha"],
            font_size=danmaku_config["font_size"],
            static_time=danmaku_config["static_time"],
        )
        _LOGGER.info(f"视频弹幕生成完成")
        if danmaku_config["number"] is None:
            return True
        else:
            _LOGGER.info(f"开始随机删除弹幕到 {danmaku_config['number']} 条")
            res = await remove_some_danmaku(path, danmaku_config["number"])
            if res is True:
                return True
            else:
                return False
    except exceptions.DanmakuClosedException:
        _LOGGER.warning(f"弹幕已关闭，停止下载")
        return True


async def download_subtitle(subtitle_json_url, dst: str, filename: str) -> bool:
    """下载字幕

    :param subtitle_json_url: 字幕json地址
    :param dst: 保存路径
    :param filename: 文件名，不包含后缀

    :return: 是否下载成功
    """
    # 使用异步下载
    client = httpx.AsyncClient()
    json_cc = await client.get(subtitle_json_url)
    if json_cc.status_code == 200:
        json_cc = json.loads(json_cc.text)
    else:
        _LOGGER.error(f"字幕json下载失败，状态码为：{json_cc.status_code}，内容为：{json_cc.text}")
        return False
    res = await ccjson2srt.ccjson2srt(json_cc, dst, filename)
    if res:
        _LOGGER.info(f"字幕下载完成，保存路径为：{dst}/{filename}.srt")
        return True
    else:
        _LOGGER.error(f"字幕下载失败")
        return False

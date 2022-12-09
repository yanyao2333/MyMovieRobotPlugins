"""
movie-robot快捷指令对接
"""
import asyncio
import logging
import os
import re
import traceback

from bilibili_api import parse_link, sync, ResourceType, video
from mbot.core.params import ArgSchema, ArgType
from mbot.core.plugins import plugin, PluginCommandContext, PluginCommandResponse

from . import bilibili_main

_LOGGER = logging.getLogger(__name__)


def find_bv(url):
    bv = re.search(r'(?<=BV)[\w\d]+', url)
    if bv:
        return "BV" + bv.group(0)
    return None


@plugin.command(name='sub_by_bilibili', title='下载bilibili视频', desc='下载bilibili视频并自动刮削（应该支持分P）',
                icon='CloudDownload',
                run_in_background=True)
def download(ctx: PluginCommandContext,
             video_id: ArgSchema(ArgType.String, 'BV号或网址', '需要下载的视频的BV号或网址，多个请用半角逗号隔开')):
    # 获取当前文件位置
    try:
        _LOGGER.info(os.path.abspath(__file__))
        video_id = video_id.split(',') if ',' in video_id else video_id
        _LOGGER.info(f'提交内容: {video_id}')
        if_people_path, people_path = bilibili_main.Utils.if_get_character()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = []
        if type(video_id) == list:
            for i in video_id:
                i = find_bv(i)
                if i is None:
                    return PluginCommandResponse(False, '你输入的BV号或网址中混入了怪东西，请仔细检查！')
                page = sync(video.Video(bvid=i).get_pages())
                if len(page) > 1:
                    media_path = bilibili_main.Utils.get_media_path(True)
                else:
                    media_path = bilibili_main.Utils.get_media_path(False)
                tasks.append(
                    bilibili_main.BilibiliOneVideoProcess(i, if_get_character=if_people_path,
                                                          emby_persons_path=people_path,
                                                          media_path=media_path).process())
        else:
            video_id = find_bv(video_id)
            page = sync(video.Video(bvid=video_id).get_pages())
            if len(page) > 1:
                media_path = bilibili_main.Utils.get_media_path(True)
            else:
                media_path = bilibili_main.Utils.get_media_path(False)
            tasks.append(bilibili_main.BilibiliOneVideoProcess(video_id, if_get_character=if_people_path,
                                                               emby_persons_path=people_path,
                                                               media_path=media_path).process())
        loop.run_until_complete(asyncio.wait(tasks))
        return PluginCommandResponse(True, '已下载完成，请刷新emby媒体库')
    except Exception as e:
        tracebacklog = traceback.format_exc()
        _LOGGER.error(tracebacklog)
        return PluginCommandResponse(False, '出了点小问题，请检查日志')
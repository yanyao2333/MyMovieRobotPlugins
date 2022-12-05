from mbot.core.params import ArgSchema, ArgType
from mbot.core.plugins import plugin, PluginCommandContext, PluginCommandResponse
from mbot.openapi import mbot_api

from .mr_api import *
from .process_bilibili import *

_LOGGER = logging.getLogger(__name__)
server = mbot_api


def if_get_character():
    api = ScraperApi(server.session)
    resp = api.config()
    if resp.get('use_cn_person_name'):
        return True, resp.get('person_nfo_path')
    else:
        return False, None


def get_media_path():
    api = MediaPath(server.session)
    resp = api.config()
    for i in resp.get('paths'):
        if 'bilibili' in i.get('target_dir') or 'Bilibili' in i.get('target_dir') or 'BILIBILI' in i.get('target_dir'):
            return i.get('target_dir')
        elif i.get('type') == 'movie':
            return i.get('target_dir')


@plugin.command(name='download', title='下载bilibili视频', desc='下载bilibili视频并自动刮削', icon='StarRate',
                run_in_background=True)
def download(ctx: PluginCommandContext, video_id: ArgSchema(ArgType.String, '需要下载的bv号', 'bv号')):
    # 获取当前文件位置
    _LOGGER.info(os.path.abspath(__file__))
    video_id = video_id.split(',') if ',' in video_id else video_id
    _LOGGER.info(f'video_id: {video_id}')
    if_people_path, people_path = if_get_character()
    media_path = get_media_path()
    if type(video_id) == list:
        for i in video_id:
            asyncio.run(ProcessOneVideo(i, if_get_character=if_people_path, emby_persons_path=people_path,
                                        media_path=media_path).process())
    else:
        downloader = ProcessOneVideo(video_id, if_get_character=if_people_path, emby_persons_path=people_path,
                                     media_path=media_path)
        asyncio.run(downloader.process())
    return PluginCommandResponse(True, '已提交下载任务')

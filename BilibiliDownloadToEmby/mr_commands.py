import re

from mbot.core.params import ArgSchema, ArgType
from mbot.core.plugins import plugin, PluginCommandContext, PluginCommandResponse

from .main import *

_LOGGER = logging.getLogger(__name__)


def find_bv(url):
    bv = re.search(r'(?<=BV)[\w\d]+', url)
    if bv:
        return "BV" + bv.group(0)
    return None


@plugin.command(name='download', title='下载bilibili视频', desc='下载bilibili视频并自动刮削', icon='CloudDownload',
                run_in_background=True)
def download(ctx: PluginCommandContext,
             video_id: ArgSchema(ArgType.String, 'BV号或网址', '需要下载的视频的BV号，多个请用半角逗号隔开')):
    # 获取当前文件位置
    _LOGGER.info(os.path.abspath(__file__))
    video_id = video_id.split(',') if ',' in video_id else video_id
    _LOGGER.info(f'video_id: {video_id}')
    if_people_path, people_path = Utils.if_get_character()
    media_path = Utils.get_media_path()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    if type(video_id) == list:
        for i in video_id:
            i = find_bv(i) if find_bv(i) else i
            tasks.append(BilibiliOneVideoProcess(i, if_get_character=if_people_path, emby_persons_path=people_path,
                                                 media_path=media_path).process())
    else:
        tasks.append(BilibiliOneVideoProcess(video_id, if_get_character=if_people_path, emby_persons_path=people_path,
                                             media_path=media_path).process())
    loop.run_until_complete(asyncio.wait(tasks))
    return PluginCommandResponse(True, '已下载完成，请刷新emby媒体库')

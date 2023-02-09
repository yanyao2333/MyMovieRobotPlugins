import enum

from plugins.BilibiliDownloader.utils import global_value, LOGGER
from plugins.BilibiliDownloader.mr import mr_session, mr_api

_LOGGER = LOGGER

class MediaSaveMode(enum.Enum):
    """
    媒体保存模式
    """
    NORMAL_SAVE = 0  # 按照电影格式保存单独视频
    UP_FOLDER_SAVE = 1  # 按照剧集格式将单独视频按照up主分组保存
    PARTS_VIDEO_SAVE = 2  # 最特殊的，用来按照剧集格式保存分P视频


def get_media_path(mode: MediaSaveMode) -> str or bool:
    """
    现在采用纯用户输入的方式

    :param mode: 媒体保存模式
    """
    up_folder_save_dir = global_value.get_value("up_folder_save_dir")
    normal_video_dir = global_value.get_value("normal_video_dir")
    part_video_dir = global_value.get_value("part_video_dir")
    if mode == MediaSaveMode.NORMAL_SAVE and not normal_video_dir:
        _LOGGER.error("你开启了按照电影格式保存单独视频，但是没有设置保存路径")
        return False
    elif mode == MediaSaveMode.UP_FOLDER_SAVE and not up_folder_save_dir:
        _LOGGER.error("你开启了按照剧集格式将单独视频按照up主分组保存，但是没有设置保存路径")
        return False
    elif mode == MediaSaveMode.PARTS_VIDEO_SAVE and not part_video_dir:
        _LOGGER.error("你开启了按照剧集格式保存分P视频，但是没有设置保存路径")
        return False
    if mode == MediaSaveMode.NORMAL_SAVE:
        return normal_video_dir
    elif mode == MediaSaveMode.UP_FOLDER_SAVE:
        return up_folder_save_dir
    elif mode == MediaSaveMode.PARTS_VIDEO_SAVE:
        return part_video_dir


def if_get_character():
    # """获取mr刮削配置，判断是否获取角色信息
    #
    # :return: 是否获取角色信息，角色信息保存路径
    # """
    # api = mr_api.ScraperApi(mr_session)
    # resp = api.config()
    # if resp.get("use_cn_person_name"):
    #     return True, resp.get("person_nfo_path")
    # else:
    #     return False, None
    """
    新版要求用户手动输入，不再自动获取
    """
    pass

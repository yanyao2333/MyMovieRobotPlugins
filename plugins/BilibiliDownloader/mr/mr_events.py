"""movie-robot事件注册"""

from typing import Dict
from typing import Optional

from bilibili_api import sync, Credential
from mbot.core.plugins import PluginMeta
from mbot.core.plugins import plugin
from mbot.openapi import mbot_api
from pydantic import BaseModel, validator

from plugins.BilibiliDownloader.mr import mr_cron_tasks
from plugins.BilibiliDownloader.mr import mr_notify
from plugins.BilibiliDownloader.utils import global_value, LOGGER, files, others

_LOGGER = LOGGER
server = mbot_api
local_path = global_value.get_value("local_path")


# class danmaku_config_model(BaseModel):
#     """弹幕配置"""
#
#     font_size: Optional[float] = 25
#     alpha: Optional[float] = 1
#     fly_time: Optional[float] = 7
#     static_time: Optional[float] = 5
#     number: Optional[int]
#
#     @validator("alpha")
#     def danmaku_alpha_validator(cls, v):
#         if 1 < v <= 100:
#             v = v / 100
#         elif v < 1:
#             v = v
#         else:
#             v = 1
#             _LOGGER.warning("弹幕透明度设置错误，已自动设置为1")
#         return v
#
#
# def get_danmaku_config(config: Dict):
#     """获取弹幕配置"""
#     config = {k: v for k, v in config.items() if v}
#     danmaku_config_dict = dict(danmaku_config_model.parse_obj(config))
#     _LOGGER.info(f"弹幕配置: {danmaku_config_dict}")
#     return danmaku_config_dict


class ConfigModel(BaseModel):
    agree_EULA: bool  # 是否同意用户协议
    notify_uids: list[int]  # 推送用户uid
    follow_uid_list: Optional[list[int]] = []  # 追更up主的uid
    get_user_follow_list: bool  # 是否获取用户关注列表
    ignore_uid_list: Optional[list[int]] = []  # 忽略up主的uid
    video_save_mode: others.MediaSaveMode  # 视频保存模式
    media_path: str  # 视频保存目录
    person_dir: Optional[str] = None  # 人物信息保存目录
    """弹幕配置 start"""
    font_size: Optional[float] = 25
    alpha: Optional[float] = 1
    fly_time: Optional[float] = 7
    static_time: Optional[float] = 5
    number: Optional[int]
    """弹幕配置 end"""

    @validator("agree_EULA")
    def agree_EULA_validator(cls, v):
        if v is False:
            _LOGGER.warning("您不同意用户协议，无法使用本插件，插件已停止运行")
            global_value.set_value("main_switch", False) # 关闭插件总开关
        return v

    @validator("follow_uid_list")
    def follow_uid_list_validator(cls, v):
        try:
            _ = v.split(",") if v else []
            return [int(i) for i in _] if _ else []
        except Exception:
            _LOGGER.warning("追更up主uid设置错误，已自动设置为空")
            return []

    @validator("ignore_uid_list")
    def ignore_uid_list_validator(cls, v):
        try:
            _ = v.split(",") if v else []
            return [int(i) for i in _] if _ else []
        except Exception:
            _LOGGER.warning("忽略up主uid设置错误，已自动设置为空")
            return []


    @validator("alpha")
    def danmaku_alpha_validator(cls, v):
        if 1 < v <= 100:
            v = v / 100
        elif v < 1:
            v = v
        else:
            v = 1
            _LOGGER.warning("弹幕透明度设置错误，已自动设置为1")
        return v


def check_config(config: dict):
    # if config.get("agree_EULA") is False:
    #     _LOGGER.warning("您不同意用户协议，无法使用本插件，插件已停止运行")
    #     global_value.set_value("agree_EULA", False)  # 不同意用户协议
    #     return False
    if files.CookieController().get_cookie():
        cookies = files.CookieController().get_cookie()
        if sync(
                Credential(
                    sessdata=cookies["SESSDATA"],
                    bili_jct=cookies["bili_jct"],
                    dedeuserid=cookies["DEDEUSERID"],
                ).check_valid()
        ):
            global_value.set_value(
                "credential",
                Credential(
                    sessdata=cookies["SESSDATA"],
                    bili_jct=cookies["bili_jct"],
                    dedeuserid=cookies["DEDEUSERID"],
                ),
            )
            global_value.set_value("cookie_is_valid", True)  # cookie有效
            _LOGGER.info("cookie处在有效期内，不再登录，开始启动定时任务")
    else:
        _LOGGER.info("没有cookie文件或已失效，请重新登录")
        global_value.set_value("cookie_is_valid", False)  # cookie无效
        mr_notify.Notify.send_any_text_message(
            title="b站登录过期", body="b站登录过期，请到mr插件快捷功能页点击登录b站"
        )
    # follow_uid_list = (
    #     config.get("follow_uid_list").split(",")
    #     if config.get("follow_uid_list")
    #     else []
    # )
    # ignore_uid_list = (
    #     config.get("ignore_uid_list").split(",")
    #     if config.get("ignore_uid_list")
    #     else []
    # )
    # try:
    #     follow_uid_list = [int(i) for i in follow_uid_list] if follow_uid_list else []
    # except ValueError:
    #     _LOGGER.warning("关注列表配置错误，看看你是不是把逗号写成了中文逗号！在你改过来之前，你填的东西无效")
    #     follow_uid_list = []
    # try:
    #     ignore_uid_list = [int(i) for i in ignore_uid_list] if ignore_uid_list else []
    # except ValueError:
    #     _LOGGER.warning("忽略列表配置错误，看看你是不是把逗号写成了中文逗号！在你改过来之前，你填的东西无效")
    #     ignore_uid_list = []
    # global_value.set_value("notify_uids", config.get("notify_uids"))  # 通知的uid
    # global_value.set_value("danmaku_config", get_danmaku_config(config))  # 弹幕配置
    # global_value.set_value("video_dir", config.get("video_dir"))
    # # global_value.set_value("part_video_dir", config.get("part_video_dir"))
    # global_value.set_value("up_folder_save_dir", config.get("part_video_dir"))  # 这里就不改utils的代码了，直接这样写
    # global_value.set_value("up_folder_save", config.get("up_folder_save"))
    # mr_cron_tasks.get_config(follow_uid_list, config.get("if_get_follow_list"), ignore_uid_list)
    try:
        config = dict(ConfigModel.parse_obj(config))
        global_value.set_value("config", config)
        _LOGGER.info("配置已初始化完成")
    except Exception:
        _LOGGER.exception("配置初始化失败，请检查填写是否正确，或者联系作者")
        global_value.set_value("main_switch", False)  # 关闭插件总开关
        return False


@plugin.after_setup
def _(plugin: PluginMeta, config: Dict):
    check_config(config)
    _LOGGER.info(f"BilibiliDownloader插件加载成功。")


@plugin.config_changed
def _(config: Dict):
    check_config(config)
    _LOGGER.info(f"BilibiliDownloader插件配置更新")

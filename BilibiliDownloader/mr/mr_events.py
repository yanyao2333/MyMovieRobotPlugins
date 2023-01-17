"""movie-robot事件注册"""

import json
import os
from typing import Dict

from mbot.core.plugins import PluginMeta
from mbot.core.plugins import plugin
from bilibili_api import sync, Credential
from mbot.openapi import mbot_api

from . import mr_cron_tasks
from utils import global_value, LOGGER, files
from mr import mr_notify
from .. import process_pages_video
from pydantic import BaseModel, validator
from typing import Optional

_LOGGER = LOGGER
server = mbot_api
local_path = global_value.get_value("local_path")


class danmaku_config_model(BaseModel):
    """弹幕配置"""

    font_size: Optional[float] = 25
    alpha: Optional[float] = 1
    fly_time: Optional[float] = 7
    static_time: Optional[float] = 5
    number: Optional[int]

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


def get_danmaku_config(config: Dict):
    """获取弹幕配置"""
    config = {k: v for k, v in config.items() if v}
    danmaku_config_dict = dict(danmaku_config_model.parse_obj(config))
    _LOGGER.info(f"弹幕配置: {danmaku_config_dict}")
    return danmaku_config_dict


def check_config(config: dict):
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
            global_value.set_value("cookie_is_valid", True)
            _LOGGER.info("cookie处在有效期内，不再登录，开始启动定时任务")
    else:
        _LOGGER.info("没有cookie文件或已失效，请重新登录")
        global_value.set_value("cookie_is_valid", False)
        mr_notify.Notify.send_any_text_message(
            title="b站登录过期", body="b站登录过期，请到mr插件快捷功能页点击登录b站"
        )
    follow_uid_list = (
        config.get("follow_uid_list").split(",")
        if config.get("follow_uid_list")
        else []
    )
    ignore_uid_list = (
        config.get("ignore_uid_list").split(",")
        if config.get("ignore_uid_list")
        else []
    )
    try:
        follow_uid_list = [int(i) for i in follow_uid_list] if follow_uid_list else []
    except ValueError:
        _LOGGER.warning("关注列表配置错误，看看你是不是把逗号写成了中文逗号！在你改过来之前，你填的东西无效")
        follow_uid_list = []
    try:
        ignore_uid_list = [int(i) for i in ignore_uid_list] if ignore_uid_list else []
    except ValueError:
        _LOGGER.warning("忽略列表配置错误，看看你是不是把逗号写成了中文逗号！在你改过来之前，你填的东西无效")
        ignore_uid_list = []
    global_value.set_value("danmaku_config", get_danmaku_config(config))
    global_value.set_value("video_dir", config.get("video_dir"))
    global_value.set_value("part_video_dir", config.get("part_video_dir"))
    global_value.set_value("up_folder_save_dir", config.get("part_video_dir"))  # 这里就不改utils的代码了，直接这样写，美其名曰：降低耦合
    global_value.set_value("up_folder_save", config.get("up_folder_save"))
    mr_cron_tasks.get_config(follow_uid_list, config.get("if_get_follow_list"), ignore_uid_list)
    _LOGGER.info(f"配置已初始化完成")


@plugin.after_setup
def _(plugin: PluginMeta, config: Dict):
    check_config(config)
    _LOGGER.info(f"插件加载成功。")


@plugin.config_changed
def _(config: Dict):
    check_config(config)
    _LOGGER.info(f"插件配置更新")

import json
import os
import threading
from typing import Dict

from mbot.core.plugins import PluginMeta
from mbot.core.plugins import plugin
from bilibili_api import sync, Credential
import logging
from mbot.openapi import mbot_api

from . import bilibili_main
from . import cron_tasks
from . import global_value
from . import bilibili_login
from . import process_pages_video

_LOGGER = logging.getLogger(__name__)
server = mbot_api


@plugin.after_setup
def _(plugin: PluginMeta, config: Dict):
    if os.path.exists(f"{bilibili_main.local_path}/cookies.txt"):
        cookies = json.loads(
            open(f"{bilibili_main.local_path}/cookies.txt", "r").read()
        )
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
            bilibili_main.get_config()
            process_pages_video.get_config()
    else:
        _LOGGER.info("没有cookie文件或已失效，请手动登录")
        # login = bilibili_login.LoginBilibili()
        # t1 = threading.Thread(target=login.by_scan_qrcode, name="bilibili_login")
        # t1.start()
        global_value.set_value("cookie_is_valid", False)
        server.notify.send_text_message(title="b站登录成功", to_uid=1, body="请到mr插件快捷功能页点击登录b站")
    follow_uid_list = (
        config.get("follow_uid_list").split(",")
        if config.get("follow_uid_list")
        else []
    )
    _LOGGER.info(f"插件加载成功。关注列表: {follow_uid_list}")
    cron_tasks.get_config(follow_uid_list)


@plugin.config_changed
def _(config: Dict):
    if os.path.exists(f"{bilibili_main.local_path}/cookies.txt"):
        cookies = json.loads(
            open(f"{bilibili_main.local_path}/cookies.txt", "r").read()
        )
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
        _LOGGER.info("没有cookie文件或已失效，开始登录流程")
        # login = bilibili_login.LoginBilibili()
        # t1 = threading.Thread(target=login.by_scan_qrcode, name="bilibili_login")
        # t1.start()
        global_value.set_value("cookie_is_valid", False)
        server.notify.send_text_message(title="b站登录成功", to_uid=1, body="登录过期，请到mr插件快捷功能页点击登录b站")
    follow_uid_list = (
        config.get("follow_uid_list").split(",")
        if config.get("follow_uid_list")
        else []
    )
    _LOGGER.info(f"插件配置更新。关注列表: {follow_uid_list}")
    cron_tasks.get_config(follow_uid_list)

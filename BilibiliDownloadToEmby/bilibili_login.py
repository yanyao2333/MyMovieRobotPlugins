# -*- coding:utf-8 -*-
"""改造bilibili_api的登录模块，使其能够在微信推送中显示二维码"""
import json
import os
import sys
import time
import uuid
import loguru
import logging

import PIL
import httpx
import requests
import tenacity
from bilibili_api import Credential, exceptions, video, sync
from bilibili_api.login import make_qrcode
from bilibili_api.utils.utils import get_api
from moviebotapi import MovieBotServer
from moviebotapi.core.session import AccessKeySession
from mbot.openapi import mbot_api

# from .constant import SERVER_URL, ACCESS_KEY
from . import global_value
from . import bilibili_main
from . import process_pages_video

# server = MovieBotServer(AccessKeySession(SERVER_URL, ACCESS_KEY))
server = mbot_api
API = get_api("login")
sys.stderr = open(f"{bilibili_main.local_path}/logs/pages_stderr.log", "w")
_LOGGER = logging.getLogger(__name__)
login_key = ""


def pad_image(image, target_size):
    """更改图片大小 使其能在微信推送中显示"""
    iw, ih = image.size
    w, h = target_size
    scale = min(w / iw, h / ih)
    nw = int(iw * scale)
    nh = int(ih * scale)
    image = image.resize((nw, nh), PIL.Image.Resampling.BICUBIC)
    new_image = PIL.Image.new("RGB", target_size, (255, 255, 255))
    new_image.paste(image, ((w - nw) // 2, (h - nh) // 2))
    return new_image


@tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(5))
def send_qrcode(img):
    """发送二维码(走mr推送渠道)"""
    files = {"file": ("qrcode.png", open(img, "rb"), "image/png")}
    data = {"file_id": 0, "img_type": "catBox"}
    res = requests.post(
        url="https://free-pic.hzz.cool/upload.php", files=files, data=data
    )  # 随便找了个公共图床
    res = res.json()
    if res["code"] == 200:
        url = res["data"]["url"].replace("\/", "/")
        server.notify.send_message_by_tmpl(
            title="截图扫码登录（请在120s内登录）",
            context={"pic_url": url},
            body="截图到bilibili扫码登录",
            to_uid=1,
        )
        return
    else:
        raise Exception("上传图片失败，重试中")


def events():
    """监听登录事件"""
    events_api = API["qrcode"]["get_events"]
    data = {"oauthKey": login_key}
    events = json.loads(
        requests.post(
            events_api["url"],
            data=data,
            cookies={"buvid3": str(uuid.uuid1()), "Domain": ".bilibili.com"},
        ).text
    )
    if "code" in events.keys() and events["code"] == -412:
        _LOGGER.info(events["message"] + "等待重试")
        raise exceptions.LoginError(events["message"])
    if isinstance(events["data"], dict):
        url = events["data"]["url"]
        cookies_list = url.split("?")[1].split("&")
        sessdata = ""
        bili_jct = ""
        dede = ""
        for cookie in cookies_list:
            if cookie[:8] == "SESSDATA":
                sessdata = cookie[9:]
            if cookie[:8] == "bili_jct":
                bili_jct = cookie[9:]
            if cookie[:11].upper() == "DEDEUSERID=":
                dede = cookie[11:]
        if os.path.exists(f"{bilibili_main.local_path}/cookies.txt"):
            os.remove(f"{bilibili_main.local_path}/cookies.txt")
        with open(f"{bilibili_main.local_path}/cookies.txt", "w") as f:
            f.write(
                json.dumps(
                    {"SESSDATA": sessdata, "bili_jct": bili_jct, "DEDEUSERID": dede}
                )
            )
        c = Credential(sessdata, bili_jct, dedeuserid=dede)
        credential = c
        return credential


def update_qrcode():
    global login_key, qrcode_image
    api = API["qrcode"]["get_qrcode_and_token"]
    qrcode_login_data = json.loads(httpx.get(api["url"]).text)["data"]
    print(qrcode_login_data)
    login_key = qrcode_login_data["oauthKey"]
    qrcode = qrcode_login_data["url"]
    qrcode_image = make_qrcode(qrcode)
    return qrcode_image


class LoginBilibili:
    """登录类"""

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_fixed(120),
        retry=tenacity.retry_if_exception_type(exceptions.LoginError),
    )
    def by_scan_qrcode(self):
        """扫码登录 如果没登录就无限重发"""
        _LOGGER.info("收到登录请求")
        img = update_qrcode()
        image = PIL.Image.open(img)
        image = pad_image(image, (1068, 455))
        image.save(img)
        send_qrcode(img)
        start = time.time()
        while True:
            credential = events()
            if credential:
                global_value.set_value("credential", credential)
                global_value.set_value("cookie_is_valid", True)
                bilibili_main.get_config()
                process_pages_video.get_config()
                server.notify.send_text_message(title="b站登录成功", to_uid=1, body="登录成功")
                return
            else:
                if time.time() - start > 120:
                    _LOGGER.error("登录超时")
                    raise exceptions.LoginError("登录超时 等待60s后重试")

    def by_cookie(self, SESSDATA, BILI_JCT, BUVID3):
        """cookie登录"""
        credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
        return credential


if __name__ == "__main__":
    login = LoginBilibili()
    credential = login.by_scan_qrcode()
    print(credential)
    print(sync(Credential.check_valid(credential)))

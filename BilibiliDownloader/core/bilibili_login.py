# -*- coding:utf-8 -*-
"""改造bilibili_api的登录模块，使其能够在微信推送中显示二维码"""
import json
import os
import time
import uuid

import PIL
from PIL import Image
import httpx
import requests
import tenacity
from bilibili_api import Credential, sync
from bilibili_api.login import make_qrcode
from bilibili_api.utils.utils import get_api

from utils import global_value, LOGGER, files
from BilibiliDownloader.mr import mr_notify, mr_api

API = get_api("login")
_LOGGER = LOGGER
login_key = ""

local_path = global_value.get_value("local_path")


def pad_image(image, target_size):
    """更改图片大小 使其能在微信推送中显示"""
    iw, ih = image.size
    w, h = target_size
    scale = min(w / iw, h / ih)
    nw = int(iw * scale)
    nh = int(ih * scale)
    image = image.resize((nw, nh), PIL.Image.ANTIALIAS)
    new_image = PIL.Image.new("RGB", target_size, (255, 255, 255))
    new_image.paste(image, ((w - nw) // 2, (h - nh) // 2))
    return new_image


@tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(5))
def send_qrcode(img):
    """发送二维码(走mr推送渠道)"""
    url = mr_api.upload_image(img)
    if url:
        mr_notify.Notify.send_login_qrcode(url)
    else:
        raise Exception("发送二维码失败")


def send_qrcode_by_imagebad(img):
    """在没有配置企业微信时，使用图床发送二维码"""
    files = {"image": ("qrcode.png", open(img, "rb"), "image/png")}
    res = requests.post(url="https://www.imgtp.com/api/upload", files=files)
    res = res.json()
    if res["code"] == 200:
        return res["data"]["url"]
    else:
        return False


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
    _LOGGER.info(events)
    if "code" in events.keys() and events["code"] == -412:
        _LOGGER.info(events["message"] + "二维码废弃，请重新登录")
        mr_notify.Notify.send_any_text_message("二维码废弃，请重新登录",
                                               events["message"] + "二维码废弃，请稍等一会尝试重新登陆")
        return False
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
        files.CookieController().set_cookie({"SESSDATA": sessdata, "bili_jct": bili_jct, "DEDEUSERID": dede})
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


def by_scan_qrcode():
    """扫码登录"""
    _LOGGER.info("收到登录请求，由于网络等原因，发送时间可能较长，请耐心等待")
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
            mr_notify.Notify.send_any_text_message("登录成功", "b站登录成功")
            return
        elif credential is False:
            return
        else:
            if time.time() - start > 120:
                _LOGGER.error("登录超时")
                mr_notify.Notify.send_any_text_message("登录超时", "b站登录超时，请重新点击登录按钮")
                return

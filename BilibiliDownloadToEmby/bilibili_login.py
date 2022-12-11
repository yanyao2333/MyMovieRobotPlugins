# -*- coding:utf-8 -*-
"""改造bilibili_api的登录模块，使其能够在微信推送中显示二维码"""
import json
import time
import uuid

import PIL
import httpx
import requests
import tenacity
from bilibili_api import Credential, exceptions, video, sync
from bilibili_api.login import make_qrcode
from bilibili_api.utils.utils import get_api
from moviebotapi import MovieBotServer
from moviebotapi.core.session import AccessKeySession

from constant import SERVER_URL, ACCESS_KEY

server = MovieBotServer(AccessKeySession(SERVER_URL, ACCESS_KEY))
API = get_api("login")
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
def send_qrcode(token, img):
    """发送二维码(走mr渠道)"""
    params = {'token': token}
    files = {'file': open(img, 'rb')}
    res = requests.post(url="https://tucang.cc/api/v1/upload", params=params,
                        files=files)  # 上传二维码用于发送 我是在找不到什么免登录还能有api的图床了。。。就先用这个吧，记得在下面填上token
    res = res.json()
    if res['code'] == '200':
        server.notify.send_message_by_tmpl(title="截图扫码登录（请在120s内登录）",
                                           context={'pic_url': res['data']['url']},
                                           body="截图到bilibili扫码登录")
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
    # if "code" in events.keys() and events["code"] == -412:
    #     print('nnnnnn')
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
        print(f"SESSDATA={sessdata};bili_jct={bili_jct};DEDEUSERID={dede}")
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
        wait=tenacity.wait_fixed(1), retry=tenacity.retry_if_exception_type(Exception)
    )
    def by_scan_qrcode(self):
        """扫码登录 如果没登录就无限重发"""
        token = "1670337991933e58927c9c14840038764e8858db545e4"
        img = update_qrcode()
        image = PIL.Image.open(img)
        image = pad_image(image, (300, 100))
        image.save(img)
        send_qrcode(token, img)
        start = time.time()
        while True:
            credential = events()
            if credential:
                return credential
            else:
                if time.time() - start > 120:
                    raise exceptions.LoginError("登录超时 60s后再次发送二维码")

    def by_cookie(self, SESSDATA, BILI_JCT, BUVID3):
        """cookie登录"""
        credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
        return credential


if __name__ == '__main__':
    print(LoginBilibili().by_scan_qrcode())

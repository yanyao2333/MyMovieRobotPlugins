"""movie-robot 消息通知交互"""

import time

from plugins.BilibiliDownloader.mr import server
from plugins.BilibiliDownloader.utils import LOGGER, global_value

_LOGGER = LOGGER
_server = server


class Notify:
    def __init__(self, video_info):
        """插件的所有通知方法都在这里，经由此类传递给movie-robot

        该类中从global_value中获取uid列表"""
        self.video_info = video_info
        self.uids = global_value.get_value("notify_uidd") if global_value.get_value("notify_uids") else [1]

    def send_message_by_templ(self):
        """发送模板消息"""
        raw_year = time.strftime("%Y", time.localtime(self.video_info["pubdate"]))
        title = f"✔️{self.video_info['title']} 下载完成"
        pubtime = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(self.video_info["pubdate"])
        )
        desc = self.video_info["desc"]
        duration = (
            str(self.video_info["duration"] // 60)
            if self.video_info["duration"] // 60 > 0
            else "1"
        )
        message = (
            f"视频标题：{self.video_info['title']}\n"
            f"视频作者：{self.video_info['owner']['name']}\n"
            f"发布时间：{pubtime}\n"
            f"视频时长：{duration}分钟\n"
            f"视频标签：{self.video_info['tname']}\n"
            f"·····································\n"
            f"{desc}"
        )
        link_url = f"https://www.bilibili.com/video/{self.video_info['bvid']}"
        poster_url = self.video_info["pic"]
        _LOGGER.info(f"开始发送模板消息")
        for uid in self.uids:
            _server.notify.send_message_by_tmpl(
                title=title,
                body=message,
                context={"link_url": link_url, "pic_url": poster_url},
                to_uid=uid,
            )

    def send_sys_message(self):
        """发送系统消息"""
        _LOGGER.info("开始发送系统消息")
        for uid in self.uids:
            _server.notify.send_system_message(
                title="bilibili下载完成",
                to_uid=uid,
                message=f"「{self.video_info['title']}」 下载完成，请刷新媒体库",
            )

    def send_all_way(self):
        """发送所有通知方式"""
        self.send_message_by_templ()
        self.send_sys_message()

    def send_pages_video_notify(self):
        """发送分p视频通知"""
        _LOGGER.info("开始发送分p视频通知")
        for uid in self.uids:
            _server.notify.send_system_message(
                title="🔔bilibili追更 分P视频提醒",
                to_uid=uid,
                message=f"你追更的up主 {self.video_info['owner']['name']} 发布了新的分P视频：{self.video_info['title']}\n\n由于b站相关api的限制，请自行在视频完结后手动下载",
            )
            link_url = f"https://www.bilibili.com/video/{self.video_info['bvid']}"
            poster_url = self.video_info["pic"]
            _server.notify.send_message_by_tmpl(
                title="bilibili追更 分P视频提醒",
                to_uid=uid,
                body=f"你追更的up主 {self.video_info['owner']['name']} 发布了新的分P视频：{self.video_info['title']}\n\n由于b站相关api的限制，请自行在视频完结后手动下载",
                context={"link_url": link_url, "pic_url": poster_url},
            )

    @staticmethod
    def send_login_qrcode(qrcode_url):
        """发送登录二维码"""
        _LOGGER.info("开始发送登录二维码")
        uids = global_value.get_value("uid") if global_value.get_value("uid") else [1]
        for uid in uids:
            _server.notify.send_message_by_tmpl(
                title="bilibili登录二维码",
                body="请使用手机扫描二维码登录",
                to_uid=uid,
                context={"pic_url": qrcode_url, "link_url": "https://www.bilibili.com"},
            )

    @staticmethod
    def send_any_text_message(title, body):
        """发送任意文字消息"""
        _LOGGER.info("开始发送任意消息")
        uids = global_value.get_value("uid") if global_value.get_value("uid") else [1]
        for uid in uids:
            _server.notify.send_text_message(
                title=title,
                body=body,
                to_uid=uid,
            )

    async def send_error_video_notify(self):
        """发送下载失败视频通知"""
        _LOGGER.info("开始发送下载失败视频通知")
        for uid in self.uids:
            _server.notify.send_system_message(
                title="bilibili 视频下载刮削失败",
                to_uid=uid,
                message=f"「{self.video_info['title']}」 下载失败，请检查日志",
            )
            link_url = f"https://www.bilibili.com/video/{self.video_info['bvid']}"
            poster_url = self.video_info["pic"]
            _server.notify.send_message_by_tmpl(
                title="bilibili 视频下载失败",
                to_uid=uid,
                body=f"「{self.video_info['title']}」 下载失败，请检查日志",
                context={"link_url": link_url, "pic_url": poster_url},
            )

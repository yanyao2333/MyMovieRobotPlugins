"""movie-robot api交互"""

from moviebotapi import Session

from plugins.BilibiliDownloader.mr import server


class ScraperApi:
    def __init__(self, session: Session):
        self._session: Session = session

    def config(self):
        return self._session.get("setting.get_scraper")


class MediaPath:
    def __init__(self, session: Session):
        self._session: Session = session

    def config(self):
        return self._session.get("config.get_media_path")


class NotifyConfig:
    def __init__(self, session: Session):
        self._session: Session = session

    def config(self):
        return self._session.get("setting.get_notify")

def upload_image(path: str):
    """上传图片"""
    img = server.user.upload_img_to_cloud_by_filepath(path)
    return img

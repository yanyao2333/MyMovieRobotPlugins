from moviebotapi import Session


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

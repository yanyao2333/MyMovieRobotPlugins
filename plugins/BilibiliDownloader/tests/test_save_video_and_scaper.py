import asyncio
import unittest

from plugins.BilibiliDownloader.core import main_video_process


class MyTestCase(unittest.TestCase):
    def test_A_save_video_in_uploader_folder(self):
        obj = save_video_modes.SaveOneVideo(mode=save_video_modes.SaveVideoMode.UP_FOLDER_STYLE, bvid="BV1C24y1v7qi", media_path="//BilibiliDownloader/tests/video_test", scraper_people=True, emby_people_path="//BilibiliDownloader/tests/people")
        asyncio.run(obj.run())

    def test_B_save_video_in_normal_folder(self):
        obj = save_video_modes.SaveOneVideo(mode=save_video_modes.SaveVideoMode.NORMAL_STYLE, bvid="BV1324y1z7gq", media_path="//BilibiliDownloader/tests/video_test", scraper_people=True, emby_people_path="//BilibiliDownloader/tests/people")
        asyncio.run(obj.run())



if __name__ == '__main__':
    unittest.main()

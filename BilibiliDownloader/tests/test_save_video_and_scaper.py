import unittest
from ..core import save_video_modes
import asyncio


class MyTestCase(unittest.TestCase):
    def test_A_save_video_in_uploader_folder(self):
        obj = save_video_modes.SaveOneVideo(mode=save_video_modes.SaveVideoMode.UP_FOLDER_STYLE, bvid="BV1324y1z7gq", media_path="F:/plugins/BilibiliDownloader/tests/video_test", scraper_people=True, emby_people_path="F:/plugins/BilibiliDownloader/tests/people")
        asyncio.run(obj.run())



if __name__ == '__main__':
    unittest.main()

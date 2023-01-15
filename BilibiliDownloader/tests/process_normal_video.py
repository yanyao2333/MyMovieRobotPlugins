import unittest
import asyncio

from BilibiliDownloader.core import process_video


class TestProcessVideo(unittest.TestCase):
    def test_process_video(self):
        self.assertEqual(asyncio.run(
            process_video.ProcessNormalVideo("BV1uG4y1C7Q1", video_path="./video_test", scraper_people=True,
                                             emby_people_path="./people").run()), True)

# if __name__ == '__main__':
#     asyncio.run(process_video.ProcessNormalVideo("BV1uG4y1C7Q1", video_path="./video_test", scraper_people=True,
#                                                  emby_people_path="./people").run())

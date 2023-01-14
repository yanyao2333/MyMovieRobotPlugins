import unittest
import asyncio
import sys

sys.path.insert(0, "F:\MyMovieRobotPlugins\BilibiliDownloader")

from core import gen_nfo

class TestNfoGenerator(unittest.TestCase):
    def build_media_info(self):
        media_info = {
            "title": "【Bilibili】测试视频",
            "desc": "测试视频",
            "bvid": "BV1J54y1d7ZL",
            "aid": 1,
            "cid": 1,
            "pubdate": 54689498,
            "duration": 1,
            "pic": "https://i0.hdslb.com/bfs/archive/1.jpg",
            "pages": [
                {
                    "cid": 1,
                    "part": "测试视频",
                    "duration": 1,
                }
            ],
            "staff": [
                {
                    "name": "测试",
                    "role": "测试",
                    "mid": 1,
                }
            ],
            "tags": [
                "测试",
            ],
            "owner": {
                "mid": 1,
                "name": "测试",
                "face": "https://i0.hdslb.com/bfs/face/1.jpg",
            },
            "tname": "测试",
        }
        return media_info

    def test_gen_movie_nfo(self):
        media_info = self.build_media_info()
        nfo = gen_nfo.NfoGenerator(media_info=media_info)
        print(nfo.media_info)
        nn = asyncio.run(nfo.gen_movie_nfo())
        asyncio.run(nfo.save_nfo(nn, "./movie.nfo"))
        
    def test_gen_tvshow_nfo(self):
        media_info = self.build_media_info()
        nfo = gen_nfo.NfoGenerator(media_info=media_info)
        nn = asyncio.run(nfo.gen_tvshow_nfo())
        asyncio.run(nfo.save_nfo(nn, "./tvshow.nfo"))

    def test_gen_episode_nfo(self):
        media_info = self.build_media_info()
        nfo = gen_nfo.NfoGenerator(media_info=media_info)
        nn = asyncio.run(nfo.gen_episodedetails_nfo())
        asyncio.run(nfo.save_nfo(nn, "./episode.nfo"))

    def test_gen_people_nfo(self):
        media_info = self.build_media_info()
        nfo = gen_nfo.NfoGenerator(media_info=media_info)
        nn = asyncio.run(nfo.gen_people_nfo())
        asyncio.run(nfo.save_nfo(nn, "./people.nfo"))

if __name__ == "__main__":
    unittest.main()
        

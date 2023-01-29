import unittest
import asyncio
from ..core import nfo_generator


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
        nfo = nfo_generator.NfoGenerator(media_info=media_info)
        print(nfo.media_info)
        nn = asyncio.run(nfo.gen_movie_nfo())
        asyncio.run(nfo.save_nfo(nn, "./movie.nfo"))

    def test_gen_tvshow_nfo(self):
        media_info = self.build_media_info()
        nfo = nfo_generator.NfoGenerator(media_info=media_info)
        nn = asyncio.run(nfo.gen_tvshow_nfo())
        asyncio.run(nfo.save_nfo(nn, "./tvshow.nfo"))

    def test_gen_episode_nfo(self):
        media_info = self.build_media_info()
        nfo = nfo_generator.NfoGenerator(media_info=media_info)
        nn = asyncio.run(nfo.gen_episodedetails_nfo())
        asyncio.run(nfo.save_nfo(nn, "./episode.nfo"))

    def test_gen_people_nfo(self):
        media_info = self.build_media_info()
        nfo = nfo_generator.NfoGenerator(media_info=media_info)
        nn = asyncio.run(nfo.gen_people_nfo())
        asyncio.run(nfo.save_nfo(nn, "./people.nfo"))


    def build_uploader_info(self):
        return {'mid': 1060544882, 'name': 'AI罕见', 'sex': '保密', 'face': 'https://i2.hdslb.com/bfs/face/a715d8c1bde8b110765e2077453309782b481c33.jpg', 'face_nft': 0, 'face_nft_type': 0, 'sign': '莲宝可爱捏，支持点歌', 'rank': 10000, 'level': 4, 'jointime': 0, 'moral': 0, 'silence': 0, 'coins': 0, 'fans_badge': False, 'fans_medal': {'show': False, 'wear': False, 'medal': None}, 'official': {'role': 0, 'title': '', 'desc': '', 'type': -1}, 'vip': {'type': 0, 'status': 0, 'due_date': 0, 'vip_pay_type': 0, 'theme_type': 0, 'label': {'path': '', 'text': '', 'label_theme': '', 'text_color': '', 'bg_style': 0, 'bg_color': '', 'border_color': '', 'use_img_label': True, 'img_label_uri_hans': '', 'img_label_uri_hant': '', 'img_label_uri_hans_static': 'https://i0.hdslb.com/bfs/vip/d7b702ef65a976b20ed854cbd04cb9e27341bb79.png', 'img_label_uri_hant_static': 'https://i0.hdslb.com/bfs/activity-plat/static/20220614/e369244d0b14644f5e1a06431e22a4d5/KJunwh19T5.png'}, 'avatar_subscript': 0, 'nickname_color': '', 'role': 0, 'avatar_subscript_url': '', 'tv_vip_status': 0, 'tv_vip_pay_type': 0}, 'pendant': {'pid': 0, 'name': '', 'image': '', 'expire': 0, 'image_enhance': '', 'image_enhance_frame': ''}, 'nameplate': {'nid': 0, 'name': '', 'image': '', 'image_small': '', 'level': '', 'condition': ''}, 'user_honour_info': {'mid': 0, 'colour': None, 'tags': []}, 'is_followed': False, 'top_photo': 'http://i0.hdslb.com/bfs/space/cb1c3ef50e22b6096fde67febe863494caefebad.png', 'theme': {}, 'sys_notice': {}, 'live_room': None, 'birthday': '01-01', 'school': {'name': ''}, 'profession': {'name': '', 'department': '', 'title': '', 'is_show': 0}, 'tags': None, 'series': {'user_upgrade_status': 3, 'show_upgrade_window': False}, 'is_senior_member': 0, 'mcn_info': None, 'gaia_res_type': 0, 'gaia_data': None, 'is_risk': False, 'elec': {'show_info': {'show': False, 'state': -1, 'title': '', 'icon': '', 'jump_url': ''}}, 'contract': None}

    def test_gen_tvshow_nfo_by_uploader_info(self):
        info = self.build_uploader_info()

        nfo = nfo_generator.NfoGenerator(media_info=info, uploader_folder_mode=True)
        nn = asyncio.run(nfo.gen_tvshow_nfo_by_uploader())
        asyncio.run(nfo.save_nfo(nn, "./tvshow.nfo"))





if __name__ == "__main__":
    unittest.main()

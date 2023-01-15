import unittest
import sys

sys.path.insert(0, "F:\MyMovieRobotPlugins\BilibiliDownloader")
from utils import global_value
from mr import mr_notify

class TestMrNotify(unittest.TestCase):
    def setUp(self):
        global_value.init()
        global_value.set_value("uid", 1)
        self.video_info = {
            "title": "test",
            "owner": {"name": "test"},
            "pubdate": 0,
            "duration": 900,
            "tname": "test",
            "desc": "test",
            "bvid": "test",
            "pic": "test",
        }

    # def test_send_message_by_templ(self):
    #     notify = mr_notify.Notify(self.video_info)
    #     notify.send_message_by_templ()

    # def test_send_sys_message(self):
    #     notify = mr_notify.Notify(self.video_info)
    #     notify.send_sys_message()

    def test_send_all_way(self):
        notify = mr_notify.Notify(self.video_info)
        notify.send_all_way()

    def test_send_pages_video_notify(self):
        notify = mr_notify.Notify(self.video_info)
        notify.send_pages_video_notify()

if __name__ == "__main__":
    unittest.main()
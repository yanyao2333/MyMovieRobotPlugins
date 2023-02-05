import unittest
from unittest import suite
from plugins.BilibiliDownloader.core import files
import asyncio

# global_value.init()
# global_value.set_value("local_path", r"F:\MRPlugins\BilibiliDownloader\tests")


class TestErrorVideoRecord(unittest.TestCase):
    def test_a_write_error_video(self):
        error_video = files.ErrorVideoController()
        self.assertEqual(asyncio.run(error_video.write_error_video("test", 1)), True)
        self.assertEqual(asyncio.run(error_video.write_error_video("test", 3)), True)
        self.assertEqual(asyncio.run(error_video.write_error_video("test", 3)), True)
        self.assertEqual(asyncio.run(error_video.write_error_video("qwert")), True)

    def test_b_read_error_video(self):
        error_video = files.ErrorVideoController()
        self.assertEqual(asyncio.run(error_video.read_error_video("test", 1)), (True, 0))
        self.assertEqual(asyncio.run(error_video.read_error_video("test", 3)), (True, 1))
        self.assertEqual(asyncio.run(error_video.read_error_video("zxcvb")), (False, 0))

    def test_c_delete_error_video(self):
        error_video = files.ErrorVideoController()
        self.assertEqual(asyncio.run(error_video.remove_error_video("test", 1)), True)
        self.assertEqual(asyncio.run(error_video.remove_error_video("asdfg")), False)

    def test_d_get_error_video_list(self):
        error_video = files.ErrorVideoController()
        self.assertIsInstance(asyncio.run(error_video.get_error_video_list()), list)
        self.assertEqual(asyncio.run(error_video.get_error_video_list()), [{'bvid': 'test', 'page': 3, 'retry': 1}, {'bvid': 'qwert', 'page': 0, 'retry': 0}])





if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestErrorVideoRecord))
    unittest.TextTestRunner().run(suite)

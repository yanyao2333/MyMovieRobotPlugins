import asyncio
import os
import unittest
from plugins.BilibiliDownloader.core import retry_video_process
from plugins.BilibiliDownloader.utils import global_value, files, LOGGER, others

class TestRetryVideoProcess(unittest.TestCase):
    def test_retry_video_process(self):
        global_value.init()
        local_path = os.path.split(os.path.realpath(__file__))[0]
        global_value.set_value("local_path", local_path)
        config_dict = {
            "video_save_mode": others.MediaSaveMode.UP_FOLDER_STYLE,
            "media_path": r"F:\MRPlugins\plugins\BilibiliDownloader\tests",
            "person_dir": r"F:\MRPlugins\plugins\BilibiliDownloader\tests\people",
            "font_size": 20,
            "number": 600,
            "alpha": 0.8,
            "fly_time": 7,
            "static_time": 5
        }
        global_value.set_value("config", config_dict)
        asyncio.run(files.ErrorVideoController().write_error_video("BV1iG4y1N79u"))
        LOGGER.info("111")
        self.assertEqual(
            asyncio.run(
                retry_video_process.retry_video_process(10)
            ),
            True,
        )

if __name__ == '__main__':
    unittest.main()
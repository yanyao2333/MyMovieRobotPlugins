import unittest

from plugins.BilibiliDownloader.core import downloader


class TestDownloader(unittest.TestCase):
    def test_download(self):
        url = "https://xy115x238x209x132xy.mcdn.bilivideo.cn:4483/upgcxcode/79/51/964595179/964595179_nb3-1-30032.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1673790232&gen=playurlv2&os=mcdn&oi=3730115047&trid=0000243753c3642147a2a53b61ba0b096620u&mid=0&platform=pc&upsig=f9ecc129ca4f71836ba333d34c907e47&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform&mcdnid=9003464&bvc=vod&nettype=0&orderid=0,3&buvid=f86939da-94c9-11ed-aac7-00e04a6801e0&build=0&agrr=0&bw=11719&logo=A0000100"
        path = r"E:\PycharmProjects\MovieRobotPlugins\BilibiliDownloader\tests\test.m4s"
        d = downloader.DownloadFunc(url, path)
        d.download_with_resume()


if __name__ == "__main__":
    unittest.main()

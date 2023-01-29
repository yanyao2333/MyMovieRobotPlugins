import traceback

from aiofiles import os, open

from ..utils import LOGGER, handle_error
import tenacity
import httpx

_LOGGER = LOGGER


class DownloadFunc:
    """下载类 用于下载视频和封面"""

    def __init__(self, url, path):
        """
        :param url: 需要下载的url
        :param path: 保存的位置
        """
        self.url = url
        self.path = path
        self.HEADERS = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com",
        }

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(6),
        wait=tenacity.wait_fixed(50),
        retry=tenacity.retry_if_result(lambda result: result is False),
        reraise=True,
    )
    async def download_cover(self):
        """
        下载封面
        """
        try:
            _LOGGER.info(f"开始下载url：{self.url}，保存路径：{self.path}")
            async with httpx.AsyncClient(headers=self.HEADERS) as client:
                async with client.stream("GET", self.url) as response:
                    _LOGGER.info(
                        f"本次请求请求头：{response.request.headers}，状态码：{response.status_code}"
                    )
                    async with open(self.path, "wb") as f:
                        async for data in response.aiter_bytes():
                            await f.write(data)
        except FileNotFoundError:
            _LOGGER.error(f"文件路径不存在：{self.path}，可能是被偷家了，终止本次处理，等待重试")
            return None
        except Exception as e:
            _LOGGER.error(f"下载失败，50秒后重试")
            tracebacklog = traceback.format_exc()
            _LOGGER.error("报错原因：\n" + tracebacklog)
            return False
        else:
            return True

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(6),
        wait=tenacity.wait_fixed(50),
        retry=tenacity.retry_if_result(lambda result: result is False),
        reraise=True,
    )
    async def download_with_resume(self):
        """这个是我瞎写的包含断点续传功能的下载方法"""
        try:
            async with httpx.AsyncClient() as client:
                _LOGGER.info(f"开始使用断点续传下载url：{self.url}，保存路径：{self.path}")
                response = await client.head(self.url, headers=self.HEADERS)
                file_size = int(response.headers["content-length"])
                try:
                    async with open(self.path, "rb") as file:
                        downloaded_size = len(await file.read())
                except FileNotFoundError:
                    downloaded_size = 0
                if downloaded_size < file_size:
                    self.HEADERS["range"] = f"bytes={file_size - downloaded_size}"
                    response = await client.get(self.url, headers=self.HEADERS)
                    _LOGGER.info(
                        f"本次请求请求头：{response.request.headers}，状态码：{response.status_code}"
                    )
                    if response.status_code == 416:
                        _LOGGER.info("不允许使用Range请求头或者Range请求头范围错误，回退到普通下载")
                        res, size = await self.normal_download()
                        if res is False:
                            return False, size
                        else:
                            return True, size
                    async with open(self.path, "ab") as file:
                        await file.write(response.content)
                    async with open(self.path, "rb") as file:
                        downloaded_size = len(await file.read())
                _LOGGER.info(f"下载完成，文件大小：{downloaded_size}")
                if downloaded_size == 0:
                    _LOGGER.error(f"下载的文件大小为0，50秒后重试")
                    return False
            return True, downloaded_size
        except:
            _LOGGER.error(f"下载失败 休息50秒后从失败处重试")
            tracebacklog = traceback.format_exc()
            _LOGGER.error("报错原因：\n" + tracebacklog)
            return False

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(6),
        wait=tenacity.wait_fixed(50),
        retry=tenacity.retry_if_result(lambda result: result is False),
        reraise=True,
    )
    async def normal_download(self):
        """普通下载"""
        try:
            _LOGGER.info(f"开始普通下载url：{self.url}，保存路径：{self.path}")
            async with httpx.AsyncClient(headers=self.HEADERS) as sess:
                if "range" in sess.headers:
                    del sess.headers["range"]
                resp = await sess.get(self.url)
                _LOGGER.info(f"本次请求请求头：{resp.request.headers}，状态码：{resp.status_code}")
                async with open(self.path, "wb") as f:
                    await f.write(resp.content)
                    size = len(resp.content)
                _LOGGER.info(f"下载完成，文件大小：{size}")
        except:
            _LOGGER.error(f"下载失败 休息50秒后从失败处重试")
            if await os.path.exists(self.path):
                await os.remove(self.path)
            tracebacklog = traceback.format_exc()
            _LOGGER.error("报错原因：\n" + tracebacklog)
            return False
        else:
            return True, size

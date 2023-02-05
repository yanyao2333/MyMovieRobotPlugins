"""操作文件"""
import json
import os
import shutil
import traceback

import aiofiles

from plugins.BilibiliDownloader.utils import LOGGER, global_value

local_path = global_value.get_value("local_path") + "/data"
if not os.path.exists(local_path):
    print("文件夹存在")
    os.makedirs(local_path, exist_ok=True)
_LOGGER = LOGGER
_LOGGER.info(local_path)


async def delete_video_folder(video_path: str) -> None:
    """删除视频目录 ignore_errors=True，忽略错误，请自行判断是否存在"""
    shutil.rmtree(video_path, ignore_errors=True)

def parse_str_to_int(param_dict: dict) -> dict:
    """python的json库会将为int的key转换为str，这个函数可以将其转换回来"""
    new_dict = {}
    for key, value in param_dict.items():
        if isinstance(value, (dict,)):
            res_dict = parse_str_to_int(value)
            try:
                new_key = int(key)
                new_dict[new_key] = res_dict
            except:
                new_dict[key] = res_dict
        else:
            try:
                new_key = int(key)
                new_dict[new_key] = value
            except:
                new_dict[key] = value

    return new_dict


class ErrorVideoController:
    def __init__(self) -> None:
        """
        error_video.json文件控制
        单个error_video记录json示例：{"BV1x7411L7Zv": {0 #第几P: 1 #重试次数, 1: 1}}
        """
        if not os.path.exists(f"{local_path}/error_video.json"):
            _LOGGER.info("error_video.json 文件未创建，创建1下")
            f = open(f"{local_path}/error_video.json", "w")
            f.write("{}")
            f.close()
        self.local_path = local_path + "/error_video.json"

    async def read_error_video(self, bvid: str, page: int = 0) -> bool and int:
        """根据bvid查找错误记录

        :param bvid: 视频的bvid号
        :param page: 分p号，从0开始
        :returns: 是否存在错误记录 and 重试次数
        """
        if not await self._load_json_data():
            return False, 0
        if bvid in self.json_data:
            if page in self.json_data[bvid]:
                return True, self.json_data[bvid][page]
            else:
                return False, 0
        else:
            return False, 0

    async def write_error_video(self, bvid: str, page: int = 0) -> bool:
        """写入错误记录

        :param bvid: 视频的bvid号
        :param page: 分p号，从0开始
        :return: 是否写入成功
        """
        if not await self._load_json_data():
            return False
        if bvid in self.json_data:
            if page in self.json_data[bvid]:
                self.json_data[bvid][page] += 1
            else:
                self.json_data[bvid][page] = 0  # 如果没有找到该分P，则设置初始值为0
        else:
            self.json_data[bvid] = {page: 0}
        res = await self._save_json_data()
        if not res:
            return False
        return True

    async def remove_error_video(self, bvid: str, page: int = 0) -> bool:
        """删除一条错误记录

        :param bvid: 视频的bvid号
        :param page: 分p号，从0开始
        :return: 是否删除成功
        """
        if not await self._load_json_data():
            return False
        if bvid in self.json_data:
            if page in self.json_data[bvid]:
                del self.json_data[bvid][page]
            else:
                return False
        else:
            return False
        if (
                bvid in self.json_data and not self.json_data[bvid]
        ):  # 如果该bvid下没有分P了，则删除该bvid
            del self.json_data[bvid]
        if not await self._save_json_data():
            return False
        return True

    async def get_error_video_list(self) -> list[dict[str, int or str]]:
        """获取错误列表

        Returns:
            list: 错误视频列表，每项包含bvid+page
        """
        if not await self._load_json_data():
            return []
        error_video_list = []
        for bvid in self.json_data:
            for page in self.json_data[bvid]:
                error_video_list.append({"bvid": bvid, "page": page, "retry": self.json_data[bvid][page]})
        return error_video_list

    async def _save_json_data(self) -> bool:
        """保存本次调用中产生的json数据"""
        try:
            json.dumps(self.json_data)
        except Exception:
            _LOGGER.error("json格式错误，请检查")
            _LOGGER.error(traceback.format_exc())
            return False
        async with aiofiles.open(self.local_path, "w") as f:
            await f.write(json.dumps(self.json_data, indent=4))
            _LOGGER.info(
                f"写入error_video.json成功，内容：{json.dumps(self.json_data, indent=4)}"
            )
        return True

    async def _load_json_data(self) -> bool:
        """加载json数据供调用"""
        async with aiofiles.open(self.local_path, "r") as f:
            source_data = await f.read()
            try:
                json.loads(source_data)
            except Exception:
                _LOGGER.error("json格式错误，输出错误日志后尝试重置")
                _LOGGER.error(traceback.format_exc())
                if len(source_data) == 0:
                    _LOGGER.error("json文件为空，重置1下")
                    async with aiofiles.open(self.local_path, "w") as f_w:
                        await f_w.write("{}")
                    source_data = "{}"
                    _LOGGER.info("恢复成功")
                else:
                    _LOGGER.error("恢复失败，请自行打开json文件查看问题所在")
                    return False
            self.json_data = json.loads(source_data)
            self.json_data = parse_str_to_int(self.json_data)
        return True


class CookieController:
    """Cookie.json控制器"""
    def __init__(self):
        self.local_path = local_path + "/cookie.json"
        self.cookie_json = {}

    def get_cookie(self) -> dict:
        """获取cookie

        :return: cookie值
        """
        with open(self.local_path, "r+") as f:
            data = f.read()
            if len(data) == 0:
                f.write("{}")
                return {}
            else:
                try:
                    self.cookie_json = json.loads(data)
                    return self.cookie_json
                except Exception:
                    _LOGGER.error("cookie.json格式错误，请检查")
                    _LOGGER.error(traceback.format_exc())
                    return {}

    def set_cookie(self, cookie: dict) -> bool:
        """设置cookie

        :param cookie: cookie值
        :return: 是否设置成功
        """
        try:
            json.dumps(cookie)
        except Exception:
            _LOGGER.error("cookie格式错误，请检查")
            _LOGGER.error(traceback.format_exc())
            return False
        with open(self.local_path, "w") as f:
            f.truncate(0)
            f.write(json.dumps(cookie, indent=4))
        return True


async def count_folder_num(path: str) -> int:
    """统计文件夹下文件夹的数量

    :param path: 文件夹路径
    :return: 文件夹数量
    """
    return len([name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))])

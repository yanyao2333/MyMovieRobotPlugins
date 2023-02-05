"""这块代码cv自https://github.com/uzxn/bilicc-json2srt.py/blob/main/json2srt.py"""

import math

from aiofiles import open


async def ccjson2srt(json_data: dict, save_path: str, filename: str) -> bool:
    """b站cc json转srt字幕

    :param json_data: api返回的cc json数据
    :param save_path: 保存路径
    :param filename: 文件名，不包含后缀
    :return: 是否转换成功
    """
    path = save_path + "/" + filename + ".srt"
    file = ""
    i = 1
    for data in json_data["body"]:
        start = data["from"]
        stop = data["to"]
        content = data["content"]
        file += "{}\n".format(i)
        hour = math.floor(start) // 3600
        minute = (math.floor(start) - hour * 3600) // 60
        sec = math.floor(start) - hour * 3600 - minute * 60
        minisec = int(math.modf(start)[0] * 100)
        file += (
            str(hour).zfill(2)
            + ":"
            + str(minute).zfill(2)
            + ":"
            + str(sec).zfill(2)
            + ","
            + str(minisec).zfill(2)
        )
        file += " --> "
        hour = math.floor(stop) // 3600
        minute = (math.floor(stop) - hour * 3600) // 60
        sec = math.floor(stop) - hour * 3600 - minute * 60
        minisec = abs(int(math.modf(stop)[0] * 100 - 1))
        file += (
            str(hour).zfill(2)
            + ":"
            + str(minute).zfill(2)
            + ":"
            + str(sec).zfill(2)
            + ","
            + str(minisec).zfill(2)
        )
        file += "\n" + content + "\n\n"
        i += 1
    async with open(path, "w", encoding="utf-8") as f:
        await f.write(file)
    return True

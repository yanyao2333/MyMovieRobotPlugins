import json
import os
import requests
# from .utils import LOGGER
import zipfile
import shutil
import loguru

LOGGER = loguru.logger

def get_local_version():
    """获取本地版本号

    :return: 版本号
    """
    with open("version.json", "r") as f:
        data = f.read()
        version = json.loads(data)["localVersion"]
    return version

def get_remote_version():
    """获取远程版本号

    :return: 版本号
    """
    with open("version.json", "r") as f:
        data = f.read()
        github_version_json = json.loads(data)["remoteVersionJsonUrl"]
        proxy = json.loads(data)["proxy"]
    try:
        LOGGER.info("正在获取远程版本号")
        response = requests.get(github_version_json)
        version = response.json()["localVersion"]
        return version
    except Exception:
        if proxy:
            LOGGER.exception("获取远程版本号失败，尝试使用代理获取")
            try:
                response = requests.get(proxy + github_version_json)
                version = response.json()["version"]
                return version
            except Exception:
                LOGGER.exception("使用代理获取远程版本号失败")
                return False
        else:
            LOGGER.exception("获取远程版本号失败")
            return False

def check_update():
    """检查更新

    :return: 是否有更新
    """
    local_version = get_local_version()
    remote_version = get_remote_version()
    if local_version == remote_version:
        return False
    else:
        return True

def update():
    """更新程序

    :return: 是否更新成功
    """
    with open("version.json", "r") as f:
        data = f.read()
        downlod_url = json.loads(data)["downloadUrl"]
        proxy = json.loads(data)["proxy"]
    try:
        os.makedirs("tmp", exist_ok=True)
        res = requests.get(downlod_url)
        with open("./tmp/BilibiliDownloader.zip", "wb") as f:
            f.write(res.content)
        zipfile.ZipFile("./tmp/BilibiliDownloader.zip").extractall("./tmp")
        os.remove("./tmp/BilibiliDownloader.zip")
        shutil.copytree("./tmp/MyMovieRobotPlugins-master/BilibiliDownloader", "./", dirs_exist_ok=True)
        shutil.rmtree("./tmp")
        return True
    except Exception:
        if proxy:
            LOGGER.exception("更新失败，尝试使用代理更新")
            try:
                res = requests.get(proxy + downlod_url)
                with open("./tmp/BilibiliDownloader.zip", "wb") as f:
                    f.write(res.content)
                zipfile.ZipFile("./tmp/BilibiliDownloader.zip").extractall("./tmp")
                os.remove("./tmp/BilibiliDownloader.zip")
                shutil.copytree("./tmp/MyMovieRobotPlugins-master/BilibiliDownloader", "./", dirs_exist_ok=True)
                shutil.rmtree("./tmp")
                return True
            except Exception:
                LOGGER.exception("使用代理更新失败")
                return False
        else:
            LOGGER.exception("更新失败")
            return False


if __name__ == "__main__":
    if check_update():
        update()
    else:
        print("当前已是最新版本")



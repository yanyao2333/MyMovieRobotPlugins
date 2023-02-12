import json
import logging
import os
import shutil
# from .utils import LOGGER
import zipfile

import loguru
import requests

LOGGER = loguru.logger

def get_local_version():
    """获取本地版本号

    :return: 版本号
    """
    with open("manifest.json", "r") as f:
        data = f.read()
        version = json.loads(data)["version"]
    return version

def get_remote_version():
    """获取远程版本号

    :return: 版本号
    """
    with open("version.json", "r") as f:
        data = f.read()
        github_version_json = json.loads(data)["remoteManifestUrl"]
        proxy = json.loads(data)["proxy"]
    response = requests.get(proxy + github_version_json)
    version = response.json()["version"]
    return version

def check_update():
    """检查更新

    :return: 是否有更新
    """
    local_version = get_local_version()
    remote_version = get_remote_version()
    if local_version == remote_version or local_version > remote_version:
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
    os.makedirs("tmp", exist_ok=True)
    res = requests.get(downlod_url)
    with open("./tmp/BilibiliDownloader.zip", "wb") as f:
        f.write(res.content)
    zipfile.ZipFile("./tmp/BilibiliDownloader.zip").extractall("./tmp")
    os.remove("./tmp/BilibiliDownloader.zip")
    shutil.copytree("./tmp/MyMovieRobotPlugins-master/BilibiliDownloader", "./", dirs_exist_ok=True)
    shutil.rmtree("./tmp")
    return True

def main():
    try:
        if check_update():
            update()
        else:
            LOGGER.info("【BilibiliDownloader】当前已是最新版本")
    except:
        pass


if __name__ == "__main__":
    if check_update():
        update()
    else:
        print("当前已是最新版本")



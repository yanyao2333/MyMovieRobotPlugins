import logging
import os
from .Utils import global_value

global_value.init()

_LOGGER = logging.getLogger(__name__)
_LOGGER.info("bilibili_download_to_emby:该插件处于测试阶段，可能会出现各种问题，如果出现问题请反馈给作者")
local_path = os.path.split(os.path.realpath(__file__))[0]
global_value.set_value("local_path", local_path)
_LOGGER.info("正在检查依赖模块")
dependent_modules = {
    "bilibili_api": "bilibili-api-python",
    "pydantic": "pydantic",
}
source = "https://pypi.tuna.tsinghua.edu.cn/simple"


def install():
    for module in dependent_modules:
        try:
            __import__(module)
        except ImportError:
            _LOGGER.warning(f"没找到 {module} 模块，正在尝试安装")
            os.system(f"pip install {dependent_modules[module]} -i {source}")
            _LOGGER.info(f"安装 {module} 模块成功")


install()

# from .mr.mr_events import *
# from .cron_tasks import *
# from .mr_commands import *
from .bilibili_main import *

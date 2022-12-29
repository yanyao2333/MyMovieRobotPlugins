import logging
import os
from . import global_value

global_value.init()

_LOGGER = logging.getLogger(__name__)
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

from .events import *
from .cron_tasks import *
from .mr_commands import *

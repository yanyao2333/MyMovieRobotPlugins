import logging
import os

_LOGGER = logging.getLogger(__name__)
try:
    import bilibili_api
except ImportError:
    _LOGGER.info("开始安装bilibili-api-python")
    os.system("pip install bilibili-api-python -i https://pypi.tuna.tsinghua.edu.cn/simple")
finally:
    import bilibili_api

from .commands import *

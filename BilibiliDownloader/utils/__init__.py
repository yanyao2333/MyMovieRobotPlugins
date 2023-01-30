"""工具"""

import loguru

LOGGER = loguru.logger  # 定义全局使用的日志记录器


class SysOut:
    """重定向sys.stdout"""

    def write(self, s):
        LOGGER.info(s)

    def flush(self):
        pass
from typing import Dict
from typing import Dict

from mbot.core.plugins import PluginMeta
from mbot.core.plugins import plugin

from .bot import *

_LOGGER = logging.getLogger(__name__)


@plugin.after_setup
def main(plugin: PluginMeta, config: Dict):
    proxy = config.get("proxy")
    token = config.get("token")
    start_bot = StartBot()
    if not token:
        _LOGGER.warning("DiscordBot:你没有配置token！")
        return
    else:
        _LOGGER.info(f"{plugin.manifest.title}加载成功：token: {token}, proxy: {proxy}")
        start_bot.run(token, proxy if proxy else None)

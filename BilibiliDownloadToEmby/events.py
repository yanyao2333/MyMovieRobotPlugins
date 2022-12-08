from typing import Dict

from mbot.core.plugins import PluginMeta
from mbot.core.plugins import plugin
import logging
import cron_tasks

_LOGGER = logging.getLogger(__name__)


@plugin.after_setup
def _(plugin: PluginMeta, config: Dict):
    follow_uid_list = config.get('follow_uid_list') if config.get('follow_uid_list') else []
    _LOGGER.info(f"插件加载成功：follow_uid_list: {follow_uid_list}")
    cron_tasks.get_config(follow_uid_list)


@plugin.config_changed
def _(config: Dict):
    follow_uid_list = config.get('follow_uid_list') if config.get('follow_uid_list') else []
    _LOGGER.info(f"插件配置更新：follow_uid_list: {follow_uid_list}")
    cron_tasks.get_config(follow_uid_list)

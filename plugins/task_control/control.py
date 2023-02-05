"""import task中实例化好的_TaskManager，控制定时任务"""
import typing

from mbot.core import task
import logging
from apscheduler.jobstores.base import JobLookupError
# import task


_LOGGER = logging.getLogger(__name__)


class SimpleTaskMeta(task.TaskMeta):
    def __init__(self, name):
        """构造一个只有name的“假”定时任务元数据"""
        super().__init__(None, name, None)

def get_task_meta(task_name):
    """获取一个定时任务的元数据"""
    _list = task.Tasks.get_tasks()
    for _task in _list:
        if _task.name == task_name:
            return _task
    return None

def get_tasks() -> list:
    raw_task_list = task.Tasks.get_tasks()
    task_list = []
    for _task in raw_task_list:
        task_list.append(_task.__dict__)
    _LOGGER.info(f"共有 {len(task_list)} 个定时任务")
    return task_list


def delete_task(task_name):
    """删除一个定时任务"""
    _meta = SimpleTaskMeta(task_name)
    try:
        task.Tasks.remove_task(_meta)
    except JobLookupError:
        _LOGGER.error(f"删除定时任务 【{task_name}】 失败！未找到该任务")
        return False
    _LOGGER.info(f"删除定时任务 【{task_name}】 成功！")
    return True


def edit_task(_task: typing.Union[task.Task, typing.Callable], name, desc, cron_expression=None, jitter=None,
              minutes=None, seconds=None, run_at_startup=False, run_at_startup_in_thread=False, plugin_name=None):
    _LOGGER.info(f"开始修改定时任务【{name}】")
    if delete_task(name) is False:
        return False
    _LOGGER.info("原定时任务删除完成，开始创建新定时任务")
    task.Tasks.add_task(task=_task, name=name, desc=desc, cron_expression=cron_expression, jitter=jitter, minutes=minutes,
                        seconds=seconds, run_at_startup=run_at_startup,
                        run_at_startup_in_thread=run_at_startup_in_thread, plugin_name=plugin_name)
    _LOGGER.info(f"定时任务 【{name}】 修改完成")
    return True

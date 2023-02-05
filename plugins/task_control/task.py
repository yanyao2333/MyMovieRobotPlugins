"""
系统内所有在主进程调度的任务管理，使用apscheduler调度；
想要扩展系统定时调度的任务，就实现Task接口，并利用Tasks.register类装饰器函数，把任务注册进系统，启动时会自动加载
"""
import datetime
import logging
import threading
import typing
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import List, Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask_apscheduler import APScheduler

# from mbot.core import MovieBot

_LOGGER = logging.getLogger(__name__)

"""以下两个函数是解析cron表达式的工具函数"""


def evaluate(expression):
    '''
    order of values
    year, month, day, week, day_of_week, hour, minute, second, start_date, end_date, timezone
    '''
    splitValues = expression.split()
    for i in range(0, 8):
        if (i == 0):
            if (splitValues[0] == '?'):
                year = None
            else:
                year = splitValues[0]
        if (i == 1):
            if (splitValues[1] == '?'):
                month = None
            else:
                month = splitValues[1]
        if (i == 2):
            if (splitValues[2] == '?'):
                day = None
            else:
                day = splitValues[2]
        if (i == 3):
            if (splitValues[3] == '?'):
                week = None
            else:
                week = splitValues[3]
        if (i == 4):
            if (splitValues[4] == '?'):
                day_of_week = None
            else:
                day_of_week = splitValues[4]
        if (i == 5):
            if (splitValues[5] == '?'):
                hour = None
            else:
                hour = splitValues[5]
        if (i == 6):
            if (splitValues[6] == '?'):
                minute = None
            else:
                minute = splitValues[6]
        if (i == 7):
            if (splitValues[7] == '?'):
                second = None
            else:
                second = splitValues[7]
    return year, month, day, week, day_of_week, hour, minute, second


def get_trigger(expression):
    # type: (str) -> CronTrigger
    """
    Evaluates a CronTrigger obj from cron expression
    :param expression: String representing the crons five first fields, e.g : '* * * * *'
    :return: A CronTrigger
    """
    vals = expression.split()
    vals = [(None if w == '?' else w) for w in vals]
    return CronTrigger(minute=vals[0], hour=vals[1], day=vals[2], month=vals[3], day_of_week=vals[4])


class TaskStatus(int, Enum):
    Ready = 1
    Running = 2
    Stop = 3
    Finished = 4


class TaskType(str, Enum):
    download_subtitle = '下载字幕任务'


class Task(metaclass=ABCMeta):
    """任务实现，可以被设置为定时执行的任务"""

    @abstractmethod
    def run(self):
        pass


class TaskMeta:
    """描述任务的元数据模型"""

    def __init__(self, task: typing.Callable, name, desc, cron_expression=None, jitter=None, minutes=None, seconds=None,
                 plugin_name=None):
        self.task: typing.Callable = task
        self.name = name
        self.desc = desc
        self.cron_expression = cron_expression
        self.jitter = jitter
        self.minutes = minutes
        self.seconds = seconds
        self.plugin_name = plugin_name


class _TaskManager:
    """任务管理类，维护管理系统内所有注册任务的元数据，并利用apscheduler实现任务调度"""

    def __init__(self, mbot=None):
        self.mbot = mbot
        self._scheduler = APScheduler(BackgroundScheduler(timezone="Asia/Shanghai"))
        self._tasks: Dict[str, TaskMeta] = dict()

    def init_app(self, mbot):
        self.mbot = mbot

    def add_task(self, task: typing.Union[Task, typing.Callable], name, desc, cron_expression=None, jitter=None,
                 minutes=None, seconds=None,
                 run_at_startup=False,
                 run_at_startup_in_thread=False, plugin_name=None):
        if name in self._tasks:
            return
        if not cron_expression and not minutes and not seconds:
            _LOGGER.error(f'任务没有运行频率设置: {name}({desc})')
            return
        if isinstance(task, Task):
            task = task.run
        if self._scheduler.get_job(name):
            self._scheduler.remove_job(name)
        if run_at_startup:
            if run_at_startup_in_thread:
                t = threading.Thread(target=task)
                t.start()
            else:
                task()
        if cron_expression:
            self._scheduler.add_job(
                name,
                task,
                trigger=get_trigger(cron_expression),
                start_date=datetime.datetime.now(),
                jitter=jitter if jitter is None else 0
            )
            if plugin_name:
                _LOGGER.info(f'来自插件{plugin_name}新增任务: {desc} 运行周期: {cron_expression}')
            else:
                _LOGGER.info(f'新增任务: {desc} 运行周期: {cron_expression}')
        else:
            self._scheduler.add_job(
                name,
                task,
                trigger='interval',
                minutes=minutes if minutes else 0,
                seconds=seconds if seconds else 0,
                jitter=jitter if jitter is None else 0
            )
            if plugin_name:
                _LOGGER.info(
                    f'来自插件{plugin_name}的新增任务: {desc} 运行间隔{minutes if minutes else 0}分{seconds if seconds else 0}秒')
            else:
                _LOGGER.info(f'新增任务: {desc} 运行间隔{minutes if minutes else 0}分{seconds if seconds else 0}秒')
        self._tasks.update(
            {name: TaskMeta(task, name, desc, cron_expression, jitter, minutes, seconds, plugin_name)})

    def register(self, name, desc, cron_expression=None, jitter=None, minutes=None, seconds=None, run_at_startup=False,
                 run_at_startup_in_thread=False):
        """
        装饰器函数。注册一个新任务
        :param name: 任务名称，英文，重复会跳过
        :param desc: 任务描述简介
        :param cron_expression: 任务的cron表达式周期
        :param jitter: 每次执行任务的偏移秒数
        :param minutes: 任务执行间隔分钟，不提供cron_expression时才会使用这个值
        :param seconds: 任务执行间隔秒，同上
        :return:
        """

        def decorator(cls):
            if name in self._tasks:
                return cls
            task = cls()
            self.add_task(task, name, desc, cron_expression, jitter, minutes, seconds, run_at_startup,
                          run_at_startup_in_thread)
            return cls

        return decorator

    def get_tasks(self) -> List[TaskMeta]:
        return list(self._tasks.values())

    def remove_task(self, meta: TaskMeta):
        if not meta:
            return
        self._scheduler.remove_job(meta.name)
        del self._tasks[meta.name]

    def start(self, webapp=None):
        if webapp:
            self._scheduler.init_app(webapp)
        self._scheduler.start()


"""一个任务管理的单例，外部不建议手动初始化"""
Tasks = _TaskManager()

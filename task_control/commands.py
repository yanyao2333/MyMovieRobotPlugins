from mbot.core.params import ArgSchema, ArgType
from mbot.core.plugins import plugin, PluginCommandContext, PluginCommandResponse
from . import control

def tasks_enum():
    tasks = control.get_tasks()
    enum_list = []
    for task in tasks:
        name = task["name"] + " —— " + task["desc"]
        enum_list.append({"name": name, "value": task["name"]})
    return enum_list



@plugin.command(name='edit_task', title='修改定时任务配置', desc='修改注册到mr的定时任务运行时间等', icon='HourglassFull',run_in_background=False)
def edit(ctx: PluginCommandContext,
                task: ArgSchema(ArgType.Enum, '定时任务', '选择需要修改的定时任务', enum_values=tasks_enum,
                                   multi_value=False),
                jitter: ArgSchema(ArgType.String, '随机延迟', '随机延迟时间，单位为秒，不填则无', required=False),
                cron_expression: ArgSchema(ArgType.String, 'cron表达式', 'cron表达式，和下面minute second二选一。两者都填取cron表达式', required=False),
                minute: ArgSchema(ArgType.String, '分钟', '任务执行间隔分钟，和上面cron表达式二选一', required=False),
                second: ArgSchema(ArgType.String, '秒', '任务执行间隔秒，和上面cron表达式二选一', required=False),
                ):
    task_meta = control.get_task_meta(task)
    minute = int(minute) if minute else None
    second = int(second) if second else None
    if not task_meta:
        return PluginCommandResponse(False, "未找到该任务")
    if not jitter:
        jitter = None
    else:
        jitter = int(jitter)
    if cron_expression:
        res = control.edit_task(task_meta.task, task_meta.name, task_meta.desc, cron_expression=cron_expression, jitter=jitter, plugin_name=task_meta.plugin_name)
    elif minute or second:
        res = control.edit_task(task_meta.task, task_meta.name, task_meta.desc, minutes=minute, seconds=second, jitter=jitter, plugin_name=task_meta.plugin_name)
    else:
        return PluginCommandResponse(False, "请填写cron表达式或者minute second")
    if res is False:
        return PluginCommandResponse(False, f"修改定时 {task} 任务失败")
    return PluginCommandResponse(True, f"修改定时 {task} 任务成功")

@plugin.command(name='remove_task', title='删除定时任务', desc='删除定时任务', icon='HourglassFull',run_in_background=False)
def remove(ctx: PluginCommandContext,
                task: ArgSchema(ArgType.Enum, '定时任务', '选择需要删除的定时任务', enum_values=tasks_enum,
                                   multi_value=False),
                ):
    if control.delete_task(task) is False:
        return PluginCommandResponse(False, f"删除定时 {task} 任务失败，未找到该任务")
    return PluginCommandResponse(True, f"删除定时 {task} 任务成功")
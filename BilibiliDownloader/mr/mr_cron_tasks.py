"""movie-robot定时任务注册"""

import threading

from apscheduler.schedulers.blocking import BlockingScheduler
import asyncio
import logging

from mbot.core.plugins import plugin
from bilibili_api import sync, Credential, user
from mbot.openapi import mbot_api

from . import bilibili_main
from ..utils import global_value
from . import bilibili_login

follow_uid_list = []
if_people_path, people_path = bilibili_main.Utils.if_get_character()
_LOGGER = logging.getLogger(__name__)
sched = BlockingScheduler()
server = mbot_api
cookie_check_num = 0
follow_check_parts = 0
follow_check_now_parts = 0


def get_config(follow_uid, if_get_follow_list, ignore_uid_list):
    global follow_uid_list
    follow_uid_list = []
    if if_get_follow_list:
        follow_uid_list = get_user_follow_list()
        follow_uid_list += follow_uid
    else:
        follow_uid_list = follow_uid
    if ignore_uid_list:
        for i in ignore_uid_list:
            if i in follow_uid_list:
                follow_uid_list.remove(i)
    _LOGGER.info(f"最终追更列表：{follow_uid_list}")
    get_limit_parts(follow_uid_list)


def get_user_follow_list():
    """获取用户关注列表"""
    _LOGGER.info("正在获取用户关注列表")
    # _LOGGER.info(str(global_value.get_value("cookie_is_valid"))+ "           "+str(global_value.get_value("credential")))
    if (
            global_value.get_value("cookie_is_valid")
            and global_value.get_value("credential") is not None
    ):
        cre = global_value.get_value("credential")
        uid = cre.dedeuserid
        follow_list = sync(user.User(credential=cre, uid=uid).get_followings())
        total_follow = follow_list["total"]
        refresh_num = total_follow // 50 + 1
        follow_list = []
        for i in range(1, refresh_num + 1):
            follow_list.extend(
                sync(user.User(credential=cre, uid=uid).get_followings(pn=i))["list"]
            )
        for i in follow_list:
            follow_uid_list.append(str(i["mid"]))
        _LOGGER.info(f"获取到关注列表: {follow_uid_list}")
        return follow_uid_list
    else:
        _LOGGER.info("cookie失效或还没登陆，无法获取关注列表")
        return []


@plugin.task("retry_download", "重新下载之前报错的视频", cron_expression="*/7 * * * *")
def retry_download():
    # 重试下载
    if not global_value.get_value("cookie_is_valid"):
        _LOGGER.warning("还没登录bilibili账号，查询是否有需要重试下载的视频任务停止运行")
        return False
    _LOGGER.info("开始运行定时任务：查询是否有需要重试下载的视频")
    asyncio.run(bilibili_main.retry_video())


@plugin.task("check_up_update", "查询追更的up主是否更新", cron_expression="*/2 * * * *")
def check_update():
    # 检查视频更新
    if not global_value.get_value("cookie_is_valid"):
        _LOGGER.warning("还没登录bilibili账号，查询追更的up主是否更新任务停止运行")
        return False
    _LOGGER.info("开始运行定时任务：查询追更的up主是否更新")
    media_path = bilibili_main.Utils.get_media_path(False)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    if not follow_uid_list:
        return
    elif media_path is False:
        _LOGGER.warning("还没设置媒体库路径，查询追更的up主是否更新任务停止运行")
        return
    follow_list = check_up_update_limit()
    _LOGGER.info(f"开始查询{follow_list}是否更新")
    for i in follow_list:
        update = bilibili_main.ListenUploadVideo(
            i, if_people_path, media_path, people_path
        )
        tasks.append(update.listen_no_pages_video_new())
    loop.run_until_complete(asyncio.wait(tasks))


def check_up_update_limit():
    """对检查更新的up主进行分组，每组20个，防止api限流"""
    global follow_check_parts, follow_check_now_parts
    if len(follow_uid_list) <= 20:
        # 如果关注列表小于20个，直接返回，跳过分组
        _LOGGER.info("关注列表小于20个，跳过分组，直接返回")
        return follow_uid_list
    if follow_check_now_parts < follow_check_parts:
        _LOGGER.info(
            f"开始检查第{follow_check_now_parts + 1}组up主是否更新，共{follow_check_parts}组，该组up主列表：{follow_uid_list[follow_check_now_parts * 20:follow_check_now_parts * 20 + 20]}"
        )
        follow_check_now_parts += 1
        return follow_uid_list[
               (follow_check_now_parts - 1) * 20: follow_check_now_parts * 20
               ]
    else:
        _LOGGER.info("检查更新的up主已经全部检查完毕，重新开始新一轮检查")
        _LOGGER.info(
            f"开始检查第{follow_check_now_parts + 1}组up主是否更新，共{follow_check_parts}组，该组up主列表：{follow_uid_list[follow_check_now_parts * 20:follow_check_now_parts * 20 + 20]}"
        )
        follow_check_now_parts = 0
        follow_check_now_parts += 1
        return follow_uid_list[
               (follow_check_now_parts - 1) * 20: follow_check_now_parts * 20
               ]


def get_limit_parts(follow_uid_list):
    global follow_check_parts
    follow_check_parts = len(follow_uid_list) // 20 + 1
    _LOGGER.info(f"关注列表分为{follow_check_parts}组，每组20个")
    return True


# def checkk_up_update_limit():
#     follow = ["123", "456", "789", "101112", "131415", "161718", "192021", "222324", "252627", "282930", "313233", "343536", "373839", "404142", "434445", "464748", "495051", "525354", "555657", "585960", "616263", "646566", "676869", "707172", "737475", "767778", "798081", "828384", "858687", "888990", "919293", "949596", "979899", "1010101", "1040104", "1070107", "1100110", "1130113", "116011", "1190119", "1220122", "1250125", "1280128", "1310131", "1340134", "1370137", "1400140", "1430143", "1460146", "1490149", "1520152", "1550155", "1580158", "1610161", "1640164", "1670167", "1700170", "1730173", "1760176", "1790179", "1820182", "1850185", "1880188", "1910191", "1940194", "1970197", "2000200", "2030203", "2060206", "2090209", "2120212", "2150215", "2180218", "2210221", "2240224", "2270227", "2300230", "2330233", "2360236", "2390239", "2420242", "2450245", "2480248", "2510251", "2540254", "2570257", "2600260", "2630263", "2660266", "2690269", "2720272", "2750275", "2780278", "2810281", "2840284", "2870287", "2900290", "2930293", "2960296", "2990299", "3020302", "3050305", "3080308", "3110311", "3140314", "3170317", "3200320", "3230323", "3260326", "3290329", "3320332", "3350335", "3380338", "3410341", "3440344", "3470347", "3500350", "3530353", "3560356", "3590359", "3620362", "3650365", "3680368", "3710371", "3740374", "3770377", "3800380", "3830383", "3860386", "3890389", "3920392", "3950395", "3980398", "4010401", "4040404", "4070407", "4100410", "4130413", "4160416"]
#     print(len(follow))
#     get_limit_parts(follow)
#     print(follow_check_parts)
#     for i in range(follow_check_parts + 20):
#         print("follow_check_now_parts: "+ str(follow_check_now_parts))
#         follow_list = check_up_update_limit(follow)
#         print(follow_list)


@plugin.task("check_cookie_is_valid", "检查cookie是否过期", cron_expression="*/2 * * * *")
def check_cookie_is_valid():
    # 检查cookie是否过期
    # _LOGGER.info("开始运行定时任务：检查cookie是否过期")
    global cookie_check_num
    cookies = global_value.get_value("credential")
    # is_ = global_value.get_value("is_cookie_valid")
    # _LOGGER.info(f"cookie是否有效：{is_}，cookie:{cookies}")
    # if global_value.get_value("is_cookie_valid"):
    #     _LOGGER.info("cookie在有效期内，跳过")
    #     return
    if cookies is None:
        cookies = {"SESSDATA": None, "bili_jct": None}
    else:
        cookies = cookies.get_cookies()
    # _LOGGER.info(cookies)
    if sync(
            Credential(
                sessdata=cookies["SESSDATA"],
                bili_jct=cookies["bili_jct"],
            ).check_valid()
    ):
        global_value.set_value("is_cookie_valid", True)
        # _LOGGER.info("cookie有效")
    else:
        _LOGGER.info("cookie已过期或没登录，请重新登录")
        global_value.set_value("is_cookie_valid", False)
        # _LOGGER.info("扫描次数："+str(num))
        if cookie_check_num == 30:
            server.notify.send_text_message(
                title="b站cookie过期，请重新扫码登录",
                to_uid=1,
                body="登录失效，请去mr的插件快捷功能页点击扫码登录按钮，并进行登陆",
            )
            cookie_check_num = 0
        else:
            cookie_check_num += 1

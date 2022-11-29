import logging
import asyncio
import os
import re
import threading
from typing import Dict
import time
import inspect
import ctypes
from mbot.core.plugins import PluginMeta
from mbot.core.plugins import plugin
import datetime
from typing import Optional
# from moviebotapi import MovieBotServer
# from moviebotapi.core.session import AccessKeySession

from mbot.openapi import mbot_api

server = mbot_api
# server = MovieBotServer(AccessKeySession('http://192.168.5.208:1329', '6eUk9TKHOdnm8FqfZ5tWS0Dpj4xBLizX'))
_LOGGER = logging.getLogger(__name__)
try:
    import discord
    from discord import app_commands, client
    from discord.ext import commands
except ImportError:
    _LOGGER.info("开始安装discord.py")
    os.system("pip install discord.py -i https://pypi.tuna.tsinghua.edu.cn/simple")
finally:
    import discord
    from discord import app_commands, client
    from discord.ext import commands

MY_GUILD = []
TOKEN = None
PROXY = None
bot = None
DiscordMainThread = None
CHANNEL_ID = None



# 网上找的，用于强制关闭线程
def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        _LOGGER.warning("Thread not found")
        return False
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


@plugin.after_setup
def _(plugin: PluginMeta, config: Dict):
    global PROXY, MY_GUILD, TOKEN, bot, DiscordMainThread, CHANNEL_ID
    PROXY = config.get("proxy")
    CHANNEL_ID = config.get("channel_id")
    MY_GUILD = config.get("guild_id")
    if MY_GUILD:
        MY_GUILD = MY_GUILD.split(",")
        for i in range(len(MY_GUILD)):
            MY_GUILD[i] = discord.Object(id=MY_GUILD[i])
    TOKEN = config.get("token")
    if not TOKEN:
        _LOGGER.warning("DiscordBot:你没有配置token！")
        return
    else:
        _LOGGER.info(f"{plugin.manifest.title}加载成功, proxy:{PROXY}, token:{TOKEN}")
        intents = discord.Intents.default()
        bot = StartBot(intents=intents, proxy=PROXY)
        set_commands()
        DiscordMainThread = threading.Thread(target=bot.run, args=(TOKEN,), name="DiscordBot")
        DiscordMainThread.start()
        _LOGGER.info(f"已启动{plugin.manifest.title}线程，请自行检查日志判断是否成功")


@plugin.config_changed
def _(config: Dict):
    global DiscordMainThread, TOKEN, bot, PROXY, MY_GUILD, CHANNEL_ID
    _LOGGER.info("DiscordBot:配置已更新，正在重启线程")
    PROXY = config.get("proxy")
    CHANNEL_ID = config.get("channel_id")
    MY_GUILD = config.get("guild_id")
    if MY_GUILD:
        MY_GUILD = MY_GUILD.split(",")
        for i in range(len(MY_GUILD)):
            MY_GUILD[i] = discord.Object(id=MY_GUILD[i])
    TOKEN = config.get("token")
    if not TOKEN:
        _LOGGER.warning("DiscordBot:你没有配置token！")
        return
    stop_thread(DiscordMainThread)
    intents = discord.Intents.default()
    bot = StartBot(intents=intents, proxy=PROXY)
    set_commands()
    _LOGGER.info("DiscordBot:线程已停止")
    DiscordMainThread = threading.Thread(target=bot.run, args=(TOKEN,))
    DiscordMainThread.start()
    _LOGGER.info("DiscordBot:线程已重启")

class MessageTemplete:
    def build_embed(self, douban_id):
        """使用豆瓣id构建Embed卡片 返回构建好的单个Embed"""
        t1 = time.time()
        _LOGGER.info(f"开始获取 豆瓣id：{douban_id} 的详细影片信息")
        douban_get = server.douban.get(douban_id)
        meta = server.meta.get_media_by_douban(media_type=douban_get.media_type, tmdb_id=douban_id)
        try:
            genres = ' / '.join(i for i in meta.genres)
            country = ' / '.join(i for i in meta.country)
            premiere_date = meta.premiere_date
            poster_url = meta.poster_url
            background_url = meta.background_url
            title = meta.title
            intro = meta.intro
        except AttributeError:
            _LOGGER.info("获取自建元数据失败，使用豆瓣信息")
            genres = ' / '.join(i for i in douban_get.genres) if douban_get.genres else "暂无"
            country = ' / '.join(i for i in douban_get.country) if douban_get.country else "暂无"
            premiere_date = douban_get.premiere_date
            poster_url = douban_get.cover_image
            background_url = None
            title = douban_get.cn_name
            intro = douban_get.intro
        if douban_get.media_type == "TV":
            type = "📺"
        else:
            type = "🎬"
        url = douban_get.url
        embed = discord.Embed(title=type + " " + title, description=intro[:150] + "······" if len(
            intro) >= 150 else intro, url=url)
        if premiere_date is None:
            premiere_date = "未播出"
        embed.set_footer(text=f"首播时间：{premiere_date}")
        embed.add_field(name="区域", value=country)
        embed.add_field(name="类型", value=genres)
        embed.set_thumbnail(url=poster_url)
        embed.set_author(name="MovieRobot")
        embed.set_image(url=background_url)
        t2 = time.time()
        _LOGGER.info("构建embed消耗时间：" + str((t2 - t1) * 1000) + "ms")
        return embed

    def build_menu(self, keyword):
        """构造由 豆瓣id+名称 组成的菜单，供用户选择后调用embed发送影片详情"""
        _LOGGER.info(f"开始获取 关键词：{keyword} 的搜索结果")
        menu = discord.ui.Select()
        search_res = server.douban.search(keyword)
        for i in range(len(search_res)):
            if search_res[i].status is None:
                status = '3'
            else:
                status = str(search_res[i].status.value)
            if status == '0':
                emoji = "⏳"
            elif status == '1':
                emoji = "✔"
            elif status == '2':
                emoji = "🔁"
            else:
                emoji = "📥"
            if str(search_res[i].rating) == "nan":
                rating = "0.0"
            else:
                rating = str(search_res[i].rating)
            menu.add_option(label=emoji + "|⭐" + rating + "|" + search_res[i].cn_name,
                            value=str(search_res[i].id) + " " + status)
        menu.callback = Callback().menu_callback
        return menu

    def build_button(self, douban_id, status):
        """构造一级菜单按钮：取消、订阅"""
        cancel_button = discord.ui.Button(label="关闭", custom_id="cancel", style=discord.ButtonStyle.danger, emoji="❌")
        if status == 0:
            status = '正在订阅️'
            status_disabled = True
            emoji = "⏳"
        elif status == 1:
            status = '订阅完成'
            status_disabled = True
            emoji = "✔"
        elif status == 2:
            status = '正在洗版'
            status_disabled = True
            emoji = "🔁"
        else:
            status = '即刻订阅'
            status_disabled = False
            emoji = "📥"
        sub_button = discord.ui.Button(label=status, custom_id=douban_id, style=discord.ButtonStyle.success,
                                       disabled=status_disabled, emoji=emoji)
        # cancel_button.callback = Callback().cancel_button_callback
        # sub_button.callback = Callback().subscribe_button_callback
        return cancel_button, sub_button

    def build_filter_button(self):
        """构建过滤器选择界面按钮"""
        filters = []
        view = discord.ui.View()
        cancel_button = discord.ui.Button(label="取消", custom_id="cancle", style=discord.ButtonStyle.danger, emoji="❌")
        cancel_button.callback = Callback().cancel_button_callback
        view.add_item(cancel_button)
        filters_get = server.subscribe.get_filters()
        auto_filter = discord.ui.Button(label="自动选择过滤器", custom_id="auto_filter",
                                        style=discord.ButtonStyle.primary, emoji="⌛")
        auto_filter.callback = Callback().subscirbe
        view.add_item(auto_filter)
        for i in range(len(filters_get)):
            temp = discord.ui.Button(label=filters_get[i].filter_name, custom_id=filters_get[i].filter_name,
                                     style=discord.ButtonStyle.primary, emoji='⌛')
            temp.callback = Callback().subscirbe
            view.add_item(temp)
        return view


class Callback:
    douban_id = None

    async def menu_callback(self, interaction: discord.Interaction):
        """一级菜单回调函数"""
        await interaction.response.defer(ephemeral=True, thinking=True)
        view = discord.ui.View()
        build_msg = MessageTemplete()
        douban_id, status = interaction.data.get("values")[0].split(" ")
        btn1, btn2 = build_msg.build_button(douban_id, int(status))
        btn1.callback = Callback().cancel_button_callback
        btn2.callback = Callback().subscribe_button_callback
        view.add_item(btn1)
        view.add_item(btn2)
        await interaction.followup.send('', embed=build_msg.build_embed(douban_id=douban_id), ephemeral=True, view=view)

    async def cancel_button_callback(self, interaction: discord.Interaction):
        """取消按钮回调函数"""
        _LOGGER.info("删除消息")
        await interaction.response.edit_message(content="这次取消了，下次一定哦！", view=None, embed=None)
        await asyncio.sleep(2.0)
        await interaction.delete_original_response()

    async def subscribe_button_callback(self, interaction: discord.Interaction):
        """订阅按钮回调函数"""
        build_msg = MessageTemplete()
        Callback.douban_id = interaction.data.get("custom_id")
        view = build_msg.build_filter_button()
        await interaction.response.edit_message(view=view)

    async def subscirbe(self, interaction: discord.Interaction):
        """订阅"""
        filter = interaction.data.get("custom_id") if interaction.data.get("custom_id") != "auto_filter" else None
        _LOGGER.info(f"开始订阅{Callback.douban_id}")
        server.subscribe.sub_by_douban(douban_id=Callback.douban_id, filter_name=filter)
        filter_msg = f"使用 {filter} 过滤器" if filter else "自动选择过滤器"
        await interaction.response.edit_message(content=f"✔ {filter_msg}订阅成功！", embed=None, view=None)
        await asyncio.sleep(2.0)
        await interaction.delete_original_response()


class StartBot(discord.Client):
    def __init__(self, *, intents: discord.Intents, proxy):
        super().__init__(intents=intents, proxy=proxy)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """设置启动钩子 同步应用命令"""
        try:
            for i in range(len(MY_GUILD)):
                self.tree.copy_global_to(guild=MY_GUILD[i])
                await self.tree.sync(guild=MY_GUILD[i])
        except AttributeError as e:
            _LOGGER.info("没有设置服务器id，无法同步应用命令，跳过")
        except discord.errors.Forbidden as e:
            _LOGGER.warning(f"服务器id：{MY_GUILD[i]} 无权限，可能是获取的id不正确，请按照教程重新获取！")
        bot.loop.create_task(run_log_loop())

    async def on_ready(self):
        """启动时执行"""
        await self.change_presence(status=discord.Status.online,
                                   activity=discord.Activity(type=discord.ActivityType.listening, name='/search'))

class GetLog:
    def __init__(self, session):
        self._ = session

    def getlog(self):
        """
        获取日志
        """
        res = self._.get('common.get_log_lines', params={'log_file': "robot.log"})
        return res

def compare_time(time1, time2):
    time1 = time.strptime(time1, "%Y/%m/%d %H:%M:%S")
    time2 = time.strptime(time2, "%Y/%m/%d %H:%M:%S")
    if time1 > time2:
        return True
    else:
        return False

def get_new_err_log(last_err_time):
    log = GetLog(server.session).getlog()
    # 遍历每一行
    for i in reversed(range(len(log))):
        # 寻找日志等级ERROR
        if "ERROR" in log[i]:
            try:
                if "Traceback" in log[i + 1]:
                    # 向下查询一佰行 打印错误信息
                    for p in range(100):
                        try:
                            if "Error" in log[i + p]:
                                temp = ""
                                for key in range(p + 1):
                                    temp += log[i + key].strip() + "\n"
                                err_time = log[i].split(" - ")[0][1:]
                                if compare_time(err_time, last_err_time):
                                    return temp, err_time
                        except IndexError:
                            pass
            except IndexError:
                if "剩余可用空间不足，跳过下载" in log[i] or "检测到CloudFlare 5秒盾" in log[i]:
                    pass
                else:
                    err_time = log[i].split(" - ")[0][1:]
                    if compare_time(err_time, last_err_time):
                        return log[i], err_time
    return None, last_err_time

async def run_log_loop():
    global last_err_time
    await bot.wait_until_ready()
    last_err_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    if CHANNEL_ID is None:
        _LOGGER.info("没有设置频道id，无法发送错误日志，跳过")
        return None
    channel = bot.get_channel(int(CHANNEL_ID))
    while not bot.is_closed():
        log, last_err_time = get_new_err_log(last_err_time)
        if log is not None:
            log = log if len(log) <= 1900 else log[:1500] + "\n\n日志过长，已截断，请去网页端查看"
            embed = discord.Embed(title="日志报错", description=f"发生时间：{last_err_time}\n```python\n" + log + "```", color=0xff0000)
            await channel.send("", embed=embed)
        await asyncio.sleep(5)


def set_commands():
    """设置应用命令"""

    @bot.tree.command()
    @app_commands.describe(
        keyword="关键词",
    )
    async def search(interaction: discord.Interaction, keyword: str):
        """通过关键词搜索影片"""
        build_msg = MessageTemplete()
        view = discord.ui.View()
        await interaction.response.send_message("🔎 请点开下面的列表进行选择",
                                                view=view.add_item(build_msg.build_menu(keyword)), delete_after=600.0)

    # @bot.tree.command()
    # async def search(interaction: discord.Interaction):
    #     """通过关键词搜索影片"""
    #     build_msg = MessageTemplete()
    #     view = discord.ui.View()
    #     await interaction.response.send_message("🔎 请点开下面的列表进行选择",
    #                                             view=view.add_item(build_msg.build_menu(keyword)), delete_after=600.0)

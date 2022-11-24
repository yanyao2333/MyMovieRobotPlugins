import asyncio
import logging
import os
import threading
import time
from io import BytesIO

import requests
from PIL import Image
from mbot.openapi import mbot_api

server = mbot_api
_LOGGER = logging.getLogger(__name__)
_LOGGER.info("开始安装discord.py")
os.system("pip install discord.py -i https://pypi.tuna.tsinghua.edu.cn/simple")
import discord


class Bot(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return
        if message.content.startswith('?search'):
            try:
                _, keyword = message.content.split(" ")
            except:
                await message.channel.send("你好像没有输入关键字，请使用**?search [关键字]**进行搜索")
                return
            build_msg = MessageTemplete()
            view = discord.ui.View()
            await message.channel.send("请点开下面的列表进行选择", view=view.add_item(build_msg.build_menu(keyword)))
        else:
            return


class StartBot:
    def __init__(self):
        self.boter = None

    def run(self, token, proxy):
        intents = discord.Intents.default()
        intents.message_content = True
        bot = Bot(proxy=proxy, intents=intents)
        t1 = threading.Thread(target=bot.run, name="DiscordThread", args=(token,))
        t1.start()


class MessageTemplete:
    def build_embed(self, douban_id):
        """使用豆瓣id构建Embed卡片 返回构建好的单个Embed"""
        t1 = time.time()
        _LOGGER.info(f"开始获取 豆瓣id：{douban_id} 的详细影片信息")
        douban_get = server.douban.get(douban_id)
        url = douban_get.url
        embed = discord.Embed(title=douban_get.cn_name, description=douban_get.intro[:150] + "······" if len(
            douban_get.intro) >= 150 else douban_get.intro, url=url)
        genres = ' / '.join(i for i in douban_get.genres)
        country = ' / '.join(i for i in douban_get.country)
        premiere_date = douban_get.premiere_date
        embed.set_footer(text=f"首播时间：{premiere_date}")
        embed.add_field(name="区域", value=country, inline=False)
        embed.add_field(name="类型", value=genres, inline=False)
        # embed.set_thumbnail(url=douban_get.cover_image)
        embed.set_author(name="MovieRobot")
        # 缩小豆瓣图片后发送（增加美观 增加了发送时间 后期可能会放弃）
        res = requests.get(douban_get.cover_image)
        img = BytesIO(res.content)
        img = Image.open(img)
        width = img.size[0]
        height = img.size[1]
        img = img.resize((int(width * 0.2), int(height * 0.2)), Image.Resampling.LANCZOS)
        img.save("image.jpg")
        self.file = discord.File("image.jpg", filename="image.jpg")
        embed.set_image(url="attachment://image.jpg")
        t2 = time.time()
        _LOGGER.info("构建embed消耗时间：" + str((t2 - t1) * 1000) + "ms")
        return embed

    def build_menu(self, keyword):
        """构造由 豆瓣id+名称 组成的菜单，供用户选择后调用embed发送影片详情"""
        menu = discord.ui.Select()
        search_res = server.douban.search(keyword)
        for i in range(len(search_res)):
            if search_res[i].status is None:
                status = '4'
            else:
                status = str(search_res[i].status.value)
            menu.add_option(label="<" + str(search_res[i].id) + ">  " + search_res[i].cn_name,
                            value=str(search_res[i].id) + " " + status)
        menu.callback = Callback().menu_callback
        return menu

    def build_button(self, douban_id, status):
        """构造一级菜单按钮：取消、订阅"""
        cancel_button = discord.ui.Button(label="关闭", custom_id="cancel", style=discord.ButtonStyle.danger)
        if status == 0:
            status = '正在订阅️'
            status_disabled = True
            emoji = "🛎"
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
        filters_get = server.subscribe.get_filters()
        for i in range(len(filters_get)):
            filters.append(filters_get[i].filter_name)


class Callback:
    async def menu_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        view = discord.ui.View()
        build_msg = MessageTemplete()
        douban_id, status = interaction.data.get("values")[0].split(" ")
        btn1, btn2 = build_msg.build_button(douban_id, int(status))
        btn1.callback = Callback().cancel_button_callback
        btn2.callback = Callback().subscribe_button_callback
        view.add_item(btn1)
        view.add_item(btn2)
        await interaction.followup.send('', embed=build_msg.build_embed(douban_id=douban_id),
                                        file=build_msg.file, ephemeral=True, view=view)

    async def cancel_button_callback(self, interaction: discord.Interaction):
        _LOGGER.info("删除消息")
        await interaction.response.edit_message(content="这次取消了，下次一定哦！", view=None, embed=None)
        await asyncio.sleep(3.0)
        await interaction.delete_original_response()

    async def subscribe_button_callback(self, interaction: discord.Interaction):
        douban_id = interaction.data.get("custom_id")
        _LOGGER.info(f"开始订阅{douban_id}")
        await interaction.response.edit_message(content="✔ 订阅成功！", embed=None, view=None)
        await asyncio.sleep(3.0)
        server.subscribe.sub_by_douban(douban_id)
        await interaction.delete_original_response()

# @boter.command()
# async def search(ctx: commands.Context, keyword: Optional[str] = None):
#     build_msg = MessageTemplete()
#     view = discord.ui.View()
#     if keyword is None:
#         await ctx.send("你好像没有输入关键字，请使用**?search [关键字]**进行搜索")
#         return None
#     await ctx.send("请点开下面的列表进行选择", view=view.add_item(build_msg.build_menu(keyword)))
#
#
# # 测试按钮回调用 记得删
# @boter.command()
# async def cmd_test(ctx: commands.Context):
#     build_msg = MessageTemplete()
#     douban_id = 35207723
#     status = 4
#     view = discord.ui.View()
#     btn1, btn2 = build_msg.build_button(douban_id, status)
#     btn1.callback = Callback().cancel_button_callback
#     btn2.callback = Callback().subscribe_button_callback
#     view.add_item(btn1)
#     view.add_item(btn2)
#     await ctx.send('', embed=build_msg.build_embed(douban_id=douban_id),
#                    file=build_msg.file, ephemeral=True, view=view)

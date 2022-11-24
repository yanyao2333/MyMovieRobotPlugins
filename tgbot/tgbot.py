import logging
from typing import Optional

from pydantic import BaseModel
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, Updater, CallbackQueryHandler

from moviebotapi import MovieBotServer
from moviebotapi.core.session import AccessKeySession
from tests.constant import SERVER_URL, ACCESS_KEY

server = MovieBotServer(AccessKeySession(SERVER_URL, ACCESS_KEY))
TOKEN = "5463464435:AAGJlIDmLcTLD-P8ZiE-tPRhRV5F3FtTjAU"
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
_LOGGER = logging.getLogger(__name__)
res = []
media_key = 0
media_num = 0
filters =
msg = "嘉然diana"


class MediaData(BaseModel):
    cn_name: str
    app_url: str
    rating: Optional[float] = 0.0
    poster_url: str
    status: Optional[str]


def start(update: Update, _: CallbackContext):
    logging.info("run '/start' event")
    update.message.reply_text("请发送 /search [名字] 搜索影片")


def mr_api_search(keyword):
    global res, media_num
    res = server.douban.search(keyword)
    media_num = len(res)
    print(media_num)
    return None


def search_res_message_template(key):
    meta = server.douban.get(res[key].id)
    intro = meta.intro
    res_year = meta.release_year
    douban_url = "https://movie.douban.com/subject/" + str(res[key].id)
    media_info = MediaData.parse_obj(res[key].__dict__)
    _next = "下一个 >"
    _previous = "< 上一个"
    if key == 0:
        _previous = "已是最前"
    if key + 1 == len(res):
        _next = "已是最后"
    status = media_info.status
    if status is None:
        status = "即刻订阅"
        status_int = 0
    else:
        status = res[key].status.value
        if status == 0:
            status = "已订阅过"
            status_int = 1
        elif status == 1:
            status = "已完成"
            status_int = 1
        elif status == 2:
            status = "洗版中"
            status_int = 1

    keyboard = [
        [
            InlineKeyboardButton(_previous, callback_data='previous'),
            InlineKeyboardButton("豆瓣", url=douban_url, callback_data=douban_url),
            InlineKeyboardButton(_next, callback_data='next')
        ],
        [InlineKeyboardButton(status, callback_data=status_int),
         InlineKeyboardButton("取消", callback_data="cancel")
         ],
    ]
    text = media_info.cn_name + f"({res_year})" + "  ⭐" + str(media_info.rating) + "\n\n" + intro
    return text, media_info.poster_url, keyboard


def search(update: Update, context: CallbackContext):
    global media_num, res, media_key, msg
    _, msg = update.message.text.split(' ')
    update.message.reply_text(f"正在搜索：{msg}")
    mr_api_search(msg)
    if media_num == 0:
        update.message.reply_text("没有搜索到任何内容")
        return None
    media_key = 0
    text, img, keyboard = search_res_message_template(media_key)
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_photo(photo=img, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup, caption=text)


def callback(update: Update, context: CallbackContext):
    global media_key
    query = update.callback_query
    query.answer()
    data = query.data
    # 前后翻页实现start（感谢WWWWW大佬提供的翻页方法🙇🙇🙇）
    if data == "previous":
        if media_key == 0:
            return None
        else:
            media_key = media_key - 1
            text, img, keyboard = search_res_message_template(media_key)
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.edit_media(media=InputMediaPhoto(img, caption=text), reply_markup=reply_markup)
    if data == "next":
        if media_key + 1 == media_num:
            return None
        else:
            media_key = media_key + 1
            text, img, keyboard = search_res_message_template(media_key)
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.edit_media(media=InputMediaPhoto(img, caption=text), reply_markup=reply_markup)
    # 前后翻页实现end
    # 选择过滤器并订阅start
    if data == '0':
        keyboard = [
            [
                InlineKeyboardButton("自动选择过滤器", callback_data='auto_filter')
            ]
        ]
        if len(filters) != 0:
            keyboard.append([])
            for key in range(len(filters)):
                filter_name = filters[key]
                keyboard[1].append(InlineKeyboardButton(filter_name, callback_data=filter_name))
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_reply_markup(reply_markup=reply_markup)
    if data in filters:
        douban_id = res[media_key].id
        cn_name = res[media_key].cn_name
        server.subscribe.sub_by_douban(douban_id, data)
        query.message.delete()
        query.message.reply_text(f"✔使用 {data} 过滤器订阅 {cn_name} 成功！")
    if data == "auto_filter":
        douban_id = res[media_key].id
        cn_name = res[media_key].cn_name
        server.subscribe.sub_by_douban(douban_id)
        query.message.delete()
        query.message.reply_text(f"✔订阅 {cn_name} 成功！")
    # 选择过滤器并订阅end
    if data == "cancel":
        query.message.delete()
        query.message.reply_text(f"🗑️已取消搜索：{msg}")


def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("search", search))
    dispatcher.add_handler(CallbackQueryHandler(callback))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

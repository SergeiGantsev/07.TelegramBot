from datetime import datetime

from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, ContextTypes, CallbackQueryHandler,
                          MessageHandler, filters, Updater, ApplicationBuilder)

from Common import get_timestamp, get_config
from MySqlCall import MySqlCall
import xml.etree.ElementTree as ET
import logging
import pathlib
from pathlib import Path

# logging
logger = logging.getLogger("TelegramBot")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d, %(name)s, %(levelname)s: %(message)s',
                              '%Y-%m-%d %H:%M:%S')

path_config = Path(pathlib.Path.cwd(), "logs", logger.name + ".log")
file_log = logging.FileHandler(filename=path_config, mode="w")
file_log.setFormatter(formatter)
logger.addHandler(file_log)

console_out = logging.StreamHandler()
console_out.setFormatter(formatter)
logger.addHandler(console_out)

telegram_token = get_config("general", "telegram_token")
# self.application = ApplicationBuilder().token(self.telegram_token).build()

application = Application.builder().token(telegram_token).build()

levels = {'level0': {'value': 0.05, 'status': 1},
          'level1': {'value': 0.6, 'status': 0},
          'level2': {'value': 1, 'status': 0}}

db = MySqlCall()

start_time = get_config("job", "start_time")
end_time = get_config("job", "end_time")
job_start_str = datetime.now().strftime("%d-%m-%Y") + f" {start_time}"
job_end_str = datetime.now().strftime("%d-%m-%Y") + f" {end_time}"

job_start = datetime.strptime(job_start_str, "%d-%m-%Y %H:%M:%S")
job_end = datetime.strptime(job_end_str, "%d-%m-%Y %H:%M:%S")


async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    command1 - Description
    command2 - Another description

    picture - Текущий арбитраж
    prices - Цены
    reset_job - Сбросить арбитраж (Админ)
    subscribe - Подписаться на события
    unsubscribe - Отписаться от событий

    """
    message = update.message

    if message.text == "/picture":
        await get_picture(update, context)

    if message.text == "/prices":
        await get_price(update, context)

    if message.text == "/subscribe":
        await subscribe(update, context)

    if message.text == "/unsubscribe":
        await unsubscribe(update, context)

    if message.text == "/reset_job":
        await reset_job(update, context)

    user = update.effective_user

    logger.info(f"User {user.name} call command {message.text}")


async def reset_job(update, context):
    user = update.effective_user

    if user.name == "@GantsevSN":
        levels['level0']['status'] = 1
        levels['level1']['status'] = 0
        levels['level2']['status'] = 0

        await update.message.reply_text("Арбитраж сброшен 🫡")
    else:
        await update.message.reply_text("Команда доступна только для Админа 👺")


async def subscribe(update, context):
    user = update.effective_user

    if not user.is_bot:
        db.start_conn()
        db.subscribe(user.id, user.first_name, user.last_name, user.username, 0)
        db.stop_conn()

        await update.message.reply_text("You are subscribed, wait information about events 👍")
    else:
        await update.message.reply_text("You are bot, sorry 😖")


async def unsubscribe(update, context):
    user = update.effective_user

    if not user.is_bot:
        db.start_conn()
        db.subscribe(user.id, user.first_name, user.last_name, user.username, 1)
        db.stop_conn()

        await update.message.reply_text("You are unsubscribed, good luck 🤝")
    else:
        await update.message.reply_text("You are bot, sorry 😖")

    # User(first_name='Сергей', id=790678999, is_bot=False, language_code='ru', last_name='Ганцев',
    #      username='GantsevSN')


async def get_picture(update, context):
    db.start_conn()
    await context.bot.send_photo(update.effective_user.id, db.get_image("canvas"))
    db.stop_conn()


async def get_price(update, context):
    db.start_conn()
    request = db.get_status()
    db.stop_conn()

    xml = ET.fromstring(request)

    date = xml.find("date").text

    text = f"Цены на _{date}_."

    bi_price = None
    binance_price = xml.find("binance_price")
    if binance_price is not None:
        bi_price = round((float(binance_price.find("ask").text) + float(binance_price.find("bid").text)) / 2, 2)
        text += f"\nBinance - *{bi_price}*"

    sp_price = None
    spot_price = xml.find("spot_price")
    if spot_price is not None:
        sp_price = round((float(spot_price.find("ask").text) + float(spot_price.find("bid").text)) / 2, 2)
        text += f"\nSpot ME - *{sp_price}*"

    if bi_price is not None and sp_price is not None:
        delta = round((bi_price - sp_price), 2)
        text += f"\nDelta: *{delta}*"

    fut_price = xml.find("fut_price")
    if fut_price is not None:
        price = round((float(fut_price.find("ask").text) + float(fut_price.find("bid").text)) / 2, 2)
        text += f"\nFUT ME - *{price}*"

    chat_id = update.effective_chat.id

    await context.bot.send_message(text=text, parse_mode="Markdown", chat_id=chat_id)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user

        keyboard = [
            [
                InlineKeyboardButton("Picture", callback_data="picture"),
                InlineKeyboardButton("Prices", callback_data="prices"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please make your choice 🤷‍", reply_markup=reply_markup)

    async def buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()

        if query.data == 'picture':
            await self.get_picture(update, context)

        if query.data == 'prices':
            await self.get_price(update, context)


async def callback_job(context):
    if job_start <= datetime.now() <= job_end:
        db.start_conn()
        prices = db.get_status()
        db.stop_conn()

        xml = ET.fromstring(prices)

        bi_price = None
        binance_price = xml.find("binance_price")
        if binance_price is not None:
            bi_price = round((float(binance_price.find("ask").text) + float(binance_price.find("bid").text)) / 2, 2)

        price = None
        spot_price = xml.find("spot_price")
        if spot_price is not None:
            price = round((float(spot_price.find("ask").text) + float(spot_price.find("bid").text)) / 2, 2)

        fut_price = xml.find("fut_price")
        if price is None and fut_price is not None:
            price = round((float(fut_price.find("ask").text) + float(fut_price.find("bid").text)) / 2, 2)

        delta = None
        if bi_price is not None and price is not None:
            delta = abs(round((bi_price - price), 2))

        message = None

        if levels['level0']['status'] == 0 and delta <= levels['level0']['value']:
            message = f"Завершение арбитража, минимальный порог пройден. Delta = {delta}"
            levels['level0']['status'] = 1
            levels['level1']['status'] = 0
            levels['level2']['status'] = 0

        if levels['level1']['status'] == 0 and delta >= levels['level1']['value']:
            message = f"Пройден ПЕРВЫЙ уровень. Delta = {delta}"
            levels['level0']['status'] = 0
            levels['level1']['status'] = 1

        if levels['level2']['status'] == 0 and delta >= levels['level2']['value']:
            message = f"Пройден ВТОРОЙ уровень. Delta = {delta}"
            levels['level0']['status'] = 0
            levels['level1']['status'] = 1
            levels['level2']['status'] = 1

        if message is not None:
            db.start_conn()
            subscribe_list = db.get_subscribes()
            db.stop_conn()

            for subscribe in subscribe_list:
                await context.bot.send_message(chat_id=subscribe, text=message)

            logger.info(f"callback_job: {message}")


def run():
    job_queue_delay = int(get_config("job", "job_queue_delay"))

    job_queue = application.job_queue
    job = job_queue.run_repeating(callback_job, interval=job_queue_delay)

    application.add_handler(CommandHandler("picture", commands))
    application.add_handler(CommandHandler("prices", commands))
    application.add_handler(CommandHandler("reset_job", commands))
    application.add_handler(CommandHandler("subscribe", commands))
    application.add_handler(CommandHandler("unsubscribe", commands))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run()

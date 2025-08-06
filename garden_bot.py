import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
import fitz
from datetime import datetime
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.INFO)

SUM, NUMBER = range(2)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("🧾 Получить сертификат")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Нажмите кнопку ниже:", reply_markup=reply_markup)
    return ConversationHandler.END

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот жив и на связи!")

async def cert_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите номинал:")
    return SUM

async def get_sum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("Ошибка: введите только цифры для номинала.")
        return SUM
    context.user_data['sum'] = user_input
    await update.message.reply_text("Введите номер сертификата:")
    return NUMBER

async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("Ошибка: введите только цифры для номера сертификата.")
        return NUMBER

    number = user_input
    context.user_data['number'] = number
    user_sum = context.user_data['sum']
    valid_until = (datetime.now() + relativedelta(months=3)).strftime("%d.%m.%Y")

    template_path = "sert_temp.pdf"
    output_path = f"сертификат_#{number}.pdf"

    try:
        doc = fitz.open(template_path)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при открытии шаблона: {e}")
        return ConversationHandler.END

    if doc.page_count < 2:
        await update.message.reply_text("Ошибка: в шаблоне должно быть минимум 2 страницы.")
        doc.close()
        return ConversationHandler.END

    page = doc[1]
    page.insert_text((165, 245), user_sum, fontsize=20, fontname="helv", color=(1, 1, 1))
    page.insert_text((180, 285), valid_until, fontsize=20, fontname="helv", color=(1, 1, 1))
    page.insert_text((20, 420), f"#{number}", fontsize=10, fontname="helv", color=(1, 1, 1))

    try:
        doc.save(output_path, incremental=False)
        doc.close()
    except Exception as e:
        await update.message.reply_text(f"Ошибка при сохранении PDF: {e}")
        return ConversationHandler.END

    try:
        with open(output_path, "rb") as f:
            await update.message.reply_document(f, filename=os.path.basename(output_path))
    except Exception as e:
        await update.message.reply_text(f"Ошибка при отправке PDF: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🧾 Получить сертификат$"), cert_entry),
            CommandHandler("cert", cert_entry),
        ],
        states={
            SUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sum)],
            NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(conv_handler)

    # Устанавливаем webhook
    app.bot.set_webhook(url=WEBHOOK_URL)

    # Запускаем webhook сервер и слушаем порт
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()

import os
import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOK = os.getenv("BOT_TOKEN")


def get_def(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

    try:
        resp = requests.get(url, timeout=10)

        if resp.status_code == 404:
            return f"❌ Слово '{word}' не найдено в словаре."

        resp.raise_for_status()
        data = resp.json()

        mean = data[0]['meanings'][0]
        defin = mean['definitions'][0]['definition']
        part = mean['partOfSpeech']

        res = f"📖 *{word}* ({part})\n\n{defin}"
        return res

    except requests.exceptions.Timeout:
        return "⏰ API словаря не отвечает. Попробуйте позже."
    except requests.exceptions.ConnectionError:
        return "🌐 Нет соединения с интернетом."
    except requests.exceptions.HTTPError as e:
        return f"⚠️ Ошибка API: {e}"
    except (KeyError, IndexError, json.JSONDecodeError):
        return "🔍 Неожиданный ответ от API. Попробуйте другое слово."


async def start(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await upd.message.reply_text(
        "👋 Привет! Я бот-словарь.\n"
        "Отправь мне любое английское слово, и я покажу его определение.\n\n"
        "📌 Команды:\n/start — приветствие\n/help — помощь\n/define слово — определение"
    )


async def help(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await upd.message.reply_text(
        "📖 *Как пользоваться*\n"
        "1. Просто напиши слово — получу определение.\n"
        "2. Или используй команду: `/define слово`\n\n"
        "Пример: `/define happiness`\n\n"
        "⚙️ Данные берутся из Free Dictionary API."
    )


async def define_cmd(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await upd.message.reply_text("✏️ Напишите слово после /define.\nПример: `/define love`")
        return

    word = ctx.args[0]
    ans = get_def(word)
    await upd.message.reply_text(ans, parse_mode="Markdown")


async def handle_txt(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    word = upd.message.text.strip().lower()
    if len(word) > 30:
        await upd.message.reply_text("📚 Слишком длинный текст. Отправьте одно слово.")
        return
    ans = get_def(word)
    await upd.message.reply_text(ans, parse_mode="Markdown")


def main():
    if not TOK:
        print("❌ Ошибка: переменная окружения BOT_TOKEN не задана")
        return

    app = Application.builder().token(TOK).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("define", define_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_txt))

    print("✅ Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
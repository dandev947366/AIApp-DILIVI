import asyncio

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.config import ICAL_URL, MODEL_ID, TELEGRAM_BOT_TOKEN
from src.services.ai_service import ai_service
from src.services.calendar_service import fetch_calendar

MAX_MESSAGE_LENGTH = 4096

HELP_TEXT = (
    "Available commands:\n"
    "/help - this list of commands\n"
    "/status - show the events from the Moodle calendar\n"
)


async def start(update: Update, context):
    await update.message.reply_text(
        "Hi! I am the AI Study Path and Career Assistant.\n\n"
        + HELP_TEXT
    )


async def help_command(update: Update, context):
    await update.message.reply_text(HELP_TEXT)


async def status(update: Update, context):
    if not ICAL_URL:
        await update.message.reply_text("Error, ical link is not set")
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    result = await asyncio.to_thread(fetch_calendar, ICAL_URL)

    if result["status"] == "error":
        await update.message.reply_text(result["message"])
        return

    lines = [f"Events found: {len(result['events'])}", ""]

    for event in result["events"]:
        lines.append(f"{event['date']:%d.%m %A}: {event['summary']}")

    await update.message.reply_text("\n".join(lines)[:MAX_MESSAGE_LENGTH])


async def chat(update: Update, context):
    await update.message.chat.send_action(ChatAction.TYPING)

    history = context.user_data.setdefault("history", [])
    question = update.message.text

    answer = await asyncio.to_thread(ai_service, question, history)

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    del history[:-4]

    await update.message.reply_text(answer[:MAX_MESSAGE_LENGTH] or "The AI returned an empty answer.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Error, bot token is not set")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print(f"Bot is running with local model: {MODEL_ID}. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()

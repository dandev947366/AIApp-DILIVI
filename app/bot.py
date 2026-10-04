import asyncio

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.config import MODEL_ID, TELEGRAM_BOT_TOKEN
from src.services.ai_service import ai_service
from src.services.calendar_service import upcoming_assignments

MAX_MESSAGE_LENGTH = 4096

HELP_TEXT = (
    "Available commands:\n"
    "/help - this list of commands\n"
    "/assignments - show upcoming assignments from the Moodle calendar\n"
    "/today - show assignments due today\n"
    "/week - show assignments due in the next 7 days\n"
)


async def start(update: Update, context):
    await update.message.reply_text(
        "Hi! I am the AI Study Path and Career Assistant.\n\n"
        + HELP_TEXT
    )


async def help_command(update: Update, context):
    await update.message.reply_text(HELP_TEXT)


async def send_assignments(update: Update, days=None):
    await update.message.chat.send_action(ChatAction.TYPING)

    result = await asyncio.to_thread(upcoming_assignments, days)

    if result["status"] == "error":
        await update.message.reply_text(result["message"])
        return

    assignments = result["assignments"]

    if not assignments:
        await update.message.reply_text("No assignments found.")
        return

    lines = [f"Assignments found: {len(assignments)}", ""]

    for item in assignments:
        lines.append(f"{item.deadline:%d.%m %A %H:%M}: {item.title}")

    await update.message.reply_text("\n".join(lines)[:MAX_MESSAGE_LENGTH])


async def assignments(update: Update, context):
    await send_assignments(update)


async def today(update: Update, context):
    await send_assignments(update, days=0)


async def week(update: Update, context):
    await send_assignments(update, days=7)


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
    application.add_handler(CommandHandler("assignments", assignments))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("week", week))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print(f"Bot is running with local model: {MODEL_ID}.")
    application.run_polling()


if __name__ == "__main__":
    main()

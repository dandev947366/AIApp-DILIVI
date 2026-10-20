import asyncio
from datetime import datetime, time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from src.config import (
    BUFFER_DAYS,
    HOURS_PER_DAY,
    MODEL_ID,
    REMINDER_TIME,
    TELEGRAM_BOT_TOKEN,
)
from src.services.ai_service import ai_service
from src.services.calendar_service import upcoming_assignments
from src.services.planning_service import build_plan

MAX_MESSAGE_LENGTH = 4096

HELP_TEXT = (
    "Available commands:\n"
    "/help - this list of commands\n"
    "/assignments - show upcoming assignments from the Moodle calendar\n"
    "/today - show assignments due today\n"
    "/week - show assignments due in the next 7 days\n"
    "/plan - AI workload estimates and when to start\n"
)


def format_assignment(item):
    return f"{item.deadline:%d.%m %A %H:%M}: {item.title}"


async def start(update: Update, context):
    context.bot_data.setdefault("chats", set()).add(update.effective_chat.id)

    await update.message.reply_text(
        "Hi! I am the AI Study Path and Career Assistant.\n\n"
        + HELP_TEXT
        + f"\nI will remind you about deadlines every day at {REMINDER_TIME}."
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
        lines.append(format_assignment(item))

    await update.message.reply_text("\n".join(lines)[:MAX_MESSAGE_LENGTH])


async def assignments(update: Update, context):
    await send_assignments(update)


async def today(update: Update, context):
    await send_assignments(update, days=0)


async def week(update: Update, context):
    await send_assignments(update, days=7)


async def plan(update: Update, context):
    await update.message.reply_text(
        "Building your study plan. New assignments are analysed by the AI, "
        "this can take a few minutes."
    )

    analyses = context.bot_data.setdefault("analyses", {})

    result = await asyncio.to_thread(build_plan, analyses)

    if result["status"] == "error":
        await update.message.reply_text(result["message"])
        return

    if not result["plan"]:
        await update.message.reply_text("No assignments found.")
        return

    lines = [f"Study plan ({HOURS_PER_DAY} h/day, {BUFFER_DAYS} day buffer):", ""]

    for row in result["plan"]:
        lines.append(format_assignment(row["assignment"]))

        if row["analysis"] is None:
            lines.append("Could not estimate the workload.")
            lines.append("")
            continue

        analysis = row["analysis"]

        lines.append(
            f"~{analysis['estimated_workload_hours']:g} h, "
            f"{analysis['difficulty']}, {analysis['task_type']}."
        )

        if row["start"] <= datetime.now().date():
            lines.append("Start now!")
        else:
            lines.append(f"Start by {row['start']:%d.%m %A}")

        lines.append("")

    await update.message.reply_text("\n".join(lines)[:MAX_MESSAGE_LENGTH])


async def send_reminders(context):
    result = await asyncio.to_thread(upcoming_assignments, 1)

    if result["status"] == "error" or not result["assignments"]:
        return

    lines = ["Reminder! Coming up today or tomorrow:", ""]

    for item in result["assignments"]:
        lines.append(format_assignment(item))

    for chat_id in context.bot_data.get("chats", set()):
        await context.bot.send_message(chat_id, "\n".join(lines)[:MAX_MESSAGE_LENGTH])


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

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .persistence(PicklePersistence(filepath="data/info.pickle"))
        .concurrent_updates(True)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("assignments", assignments))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("week", week))
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    hour, minute = REMINDER_TIME.split(":")
    reminder_time = time(int(hour), int(minute), tzinfo=datetime.now().astimezone().tzinfo)
    application.job_queue.run_daily(send_reminders, time=reminder_time)

    print(f"Bot is running with local model: {MODEL_ID}.")
    application.run_polling()


if __name__ == "__main__":
    main()

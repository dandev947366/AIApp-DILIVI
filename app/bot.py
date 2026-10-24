import asyncio
from datetime import datetime, time

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
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
from src.database import init_db
from src.services.ai_service import ai_service
from src.services.calendar_service import connect_student, student_assignments, sync_student
from src.services.planning_service import build_plan

MAX_MESSAGE_LENGTH = 4096

HELP_TEXT = (
    "Available commands:\n"
    "/help - this list of commands\n"
    "/connect <calendar link> <full name> - connect your Moodle calendar\n"
    "/sync - update assignments from Moodle\n"
    "/assignments - show upcoming assignments\n"
    "/today - show assignments due today\n"
    "/week - show assignments due in the next 7 days\n"
    "/plan - AI workload estimates and when to start\n"
)

CONNECT_TEXT = (
    "Please connect your Moodle calendar first:\n"
    "/connect <calendar link> <full name>\n\n"
    "Moodle: Calendar -> Import or export calendars -> Export calendar -> Get calendar URL"
)


def format_assignment(item):
    return f"{item.deadline:%d.%m %A %H:%M}: {item.title}"


async def start(update: Update, context):
    await update.message.reply_text(
        "Hi! I am the AI Study Path and Career Assistant.\n\n"
        + HELP_TEXT
        + f"\nAfter /connect I will remind you about deadlines every day at {REMINDER_TIME}."
    )


async def help_command(update: Update, context):
    await update.message.reply_text(HELP_TEXT)


async def connect(update: Update, context):
    if len(context.args) < 2:
        await update.message.reply_text(CONNECT_TEXT)
        return

    ical_url = context.args[0]
    full_name = " ".join(context.args[1:])

    try:
        await update.message.delete()
    except TelegramError:
        pass

    await update.effective_chat.send_action(ChatAction.TYPING)

    result = await asyncio.to_thread(connect_student, ical_url, full_name)

    if result["status"] == "error":
        await update.effective_chat.send_message(result["message"])
        return

    context.user_data["student_id"] = result["student_id"]
    context.bot_data.setdefault("students", {})[update.effective_chat.id] = result["student_id"]

    await update.effective_chat.send_message(
        f"Calendar connected for {full_name}. Events synced: {result['events']}.\n"
        "Your message with the link was deleted because the link works like a password."
    )


async def sync(update: Update, context):
    student_id = context.user_data.get("student_id")

    if student_id is None:
        await update.message.reply_text(CONNECT_TEXT)
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    result = await asyncio.to_thread(sync_student, student_id)

    if result["status"] == "error":
        await update.message.reply_text(result["message"])
        return

    await update.message.reply_text(f"Calendar updated. Events synced: {result['events']}.")


async def send_assignments(update: Update, context, days=None):
    student_id = context.user_data.get("student_id")

    if student_id is None:
        await update.message.reply_text(CONNECT_TEXT)
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    result = await asyncio.to_thread(student_assignments, student_id, days)

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
    await send_assignments(update, context)


async def today(update: Update, context):
    await send_assignments(update, context, days=0)


async def week(update: Update, context):
    await send_assignments(update, context, days=7)


async def plan(update: Update, context):
    student_id = context.user_data.get("student_id")

    if student_id is None:
        await update.message.reply_text(CONNECT_TEXT)
        return

    await update.message.reply_text(
        "Building your study plan. New assignments are analysed by the AI, "
        "this can take a few minutes."
    )

    analyses = context.bot_data.setdefault("analyses", {})

    result = await asyncio.to_thread(build_plan, student_id, analyses)

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
    for chat_id, student_id in context.bot_data.get("students", {}).items():
        await asyncio.to_thread(sync_student, student_id)

        result = await asyncio.to_thread(student_assignments, student_id, 1)

        if result["status"] == "error" or not result["assignments"]:
            continue

        lines = ["Reminder! Coming up today or tomorrow:", ""]

        for item in result["assignments"]:
            lines.append(format_assignment(item))

        await context.bot.send_message(chat_id, "\n".join(lines)[:MAX_MESSAGE_LENGTH])


async def chat(update: Update, context):
    await update.message.chat.send_action(ChatAction.TYPING)

    history = context.user_data.setdefault("history", [])
    question = update.message.text
    student_id = context.user_data.get("student_id")

    answer = await asyncio.to_thread(ai_service, question, history, student_id)

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    del history[:-4]

    await update.message.reply_text(answer[:MAX_MESSAGE_LENGTH] or "The AI returned an empty answer.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Error, bot token is not set")

    init_db()

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .persistence(PicklePersistence(filepath="data/info.pickle"))
        .concurrent_updates(True)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("sync", sync))
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

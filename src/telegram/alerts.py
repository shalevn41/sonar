import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


def _bot_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _chat_id() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", "")


async def _send(text: str):
    bot = Bot(token=_bot_token())
    await bot.send_message(chat_id=_chat_id(), text=text, parse_mode="HTML")


def send_message(text: str):
    asyncio.run(_send(text))


class TelegramAlerter:
    def send_immediate_alert(self, job: dict):
        score = job.get("ai_score", "?")
        title = job.get("title", "—")
        company = job.get("company", "—")
        location = job.get("location", "—")
        salary = job.get("salary_range", "—")
        reason = job.get("ai_reason", "—")
        red_flags = job.get("ai_red_flags", "—")
        url = job.get("url", "")

        text = (
            f"🎯 <b>משרה חדשה! ציון: {score}/100</b>\n"
            f"תפקיד: {title}\n"
            f"חברה: {company}\n"
            f"מיקום: {location} | שכר: {salary}\n"
            f"למה מתאים: {reason}\n"
            f"Red flags: {red_flags}\n"
            f'🔗 <a href="{url}">פתח משרה</a>'
        )
        send_message(text)

    def send_morning_summary(self, jobs_today: list[dict], total_scanned: int, total_new: int):
        today = datetime.now().strftime("%d/%m/%Y")
        above_80 = [j for j in jobs_today if (j.get("ai_score") or 0) >= 80]
        top3 = sorted(jobs_today, key=lambda j: j.get("ai_score") or 0, reverse=True)[:3]

        if not above_80:
            highest = max((j.get("ai_score") or 0 for j in jobs_today), default=0)
            text = (
                f"☀️ <b>סיכום בוקר - {today}</b>\n"
                f"אין משרות חדשות מעל 80 הלילה.\n"
                f"נסרקו: {total_scanned} | חדשות: {total_new} | הכי גבוה: {highest}/100"
            )
        else:
            lines = [f"☀️ <b>סיכום בוקר - {today}</b>",
                     f"נסרקו: {total_scanned} | חדשות: {total_new} | מעל 80: {len(above_80)}",
                     "", "Top 3 היום:"]
            for i, job in enumerate(top3, 1):
                lines.append(f"{i}. {job.get('title','—')} - {job.get('company','—')} ({job.get('ai_score','?')}/100)")
            text = "\n".join(lines)

        send_message(text)

    def send_stale_site_alert(self, site_name: str):
        text = (
            f"⚠️ <b>Sonar Alert</b>\n"
            f"{site_name} לא החזיר תוצאות ב-3 סריקות רצופות.\n"
            f"ייתכן שהאתר השתנה — בדוק את ה-scraper."
        )
        send_message(text)


# Telegram bot command handlers

async def cmd_top10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from src.database.db import SessionLocal
    from src.database.models import Job

    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.ai_score.isnot(None)).order_by(Job.ai_score.desc()).limit(10).all()
        if not jobs:
            await update.message.reply_text("אין משרות בדאטהבייס עדיין.")
            return
        lines = ["🏆 <b>Top 10 משרות</b>"]
        for i, j in enumerate(jobs, 1):
            lines.append(f'{i}. <a href="{j.url}">{j.title}</a> — {j.company} ({j.ai_score}/100)')
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 מתחיל סריקה...")
    from src.scraper.runner import run_scan
    run_scan()
    await update.message.reply_text("✅ סריקה הושלמה.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from src.database.db import SessionLocal
    from src.database.models import ScanLog, Job
    from sqlalchemy import func

    db = SessionLocal()
    try:
        total_scans = db.query(ScanLog).count()
        total_jobs = db.query(Job).count()
        avg_score = db.query(func.avg(Job.ai_score)).scalar()
        avg_score_str = f"{avg_score:.1f}" if avg_score else "—"
        text = (
            f"📊 <b>סטטיסטיקות Sonar</b>\n"
            f"סריקות כולל: {total_scans}\n"
            f"משרות בדאטהבייס: {total_jobs}\n"
            f"ציון ממוצע: {avg_score_str}"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    finally:
        db.close()


def build_bot_app() -> Application:
    app = Application.builder().token(_bot_token()).build()
    app.add_handler(CommandHandler("top10", cmd_top10))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("stats", cmd_stats))
    return app

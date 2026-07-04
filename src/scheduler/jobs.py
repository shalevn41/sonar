import logging
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def job_full_scan():
    logger.info("[scheduler] Running full scan (BS4 sites)...")
    from src.scraper.runner import run_scan
    run_scan()


def job_playwright_scan():
    logger.info("[scheduler] Running Playwright scan (Indeed + Glassdoor)...")
    from src.scraper.runner import run_scan
    run_scan(site="indeed")
    run_scan(site="glassdoor")


def job_morning_summary():
    logger.info("[scheduler] Sending morning summary...")
    from src.database.db import SessionLocal
    from src.database.models import Job, ScanLog
    from src.telegram.alerts import TelegramAlerter
    from datetime import timedelta

    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(hours=24)
        jobs_today = db.query(Job).filter(Job.date_found >= since).all()
        jobs_dicts = [
            {
                "title": j.title, "company": j.company, "url": j.url,
                "ai_score": j.ai_score, "location": j.location,
                "salary_range": j.salary_range, "ai_reason": j.ai_reason,
            }
            for j in jobs_today
        ]
        logs = db.query(ScanLog).filter(ScanLog.scan_date >= since).all()
        total_scanned = sum(l.jobs_found for l in logs)
        total_new = sum(l.jobs_new for l in logs)
        TelegramAlerter().send_morning_summary(jobs_dicts, total_scanned, total_new)
    finally:
        db.close()


def job_notion_backup():
    logger.info("[scheduler] Running Notion backup...")
    from src.notion.backup import NotionBackup
    NotionBackup().backup_jobs()


def job_auto_delete():
    logger.info("[scheduler] Running auto-delete of stale jobs...")
    from src.database.db import SessionLocal
    from src.database.models import Job
    from datetime import timedelta
    from sqlalchemy import and_

    db = SessionLocal()
    try:
        now = datetime.now()
        # Low score: delete after 7 days
        db.query(Job).filter(
            and_(
                Job.ai_score < 60,
                Job.status.in_(["new", "viewed"]),
                Job.date_found < now - timedelta(days=7),
            )
        ).delete(synchronize_session=False)
        # Higher score: delete after 30 days
        db.query(Job).filter(
            and_(
                Job.ai_score >= 60,
                Job.status.in_(["new", "viewed"]),
                Job.date_found < now - timedelta(days=30),
            )
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def start_scheduler():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")

    scheduler.add_job(job_full_scan, CronTrigger(hour=9, minute=0), id="scan_0900")
    scheduler.add_job(job_morning_summary, CronTrigger(hour=9, minute=0), id="morning_summary")
    scheduler.add_job(job_playwright_scan, CronTrigger(hour=9, minute=30), id="scan_playwright")
    scheduler.add_job(job_full_scan, CronTrigger(hour=13, minute=0), id="scan_1300")
    scheduler.add_job(job_full_scan, CronTrigger(hour=17, minute=0), id="scan_1700")
    scheduler.add_job(job_notion_backup, CronTrigger(hour=0, minute=0), id="notion_backup")
    scheduler.add_job(job_auto_delete, CronTrigger(hour=3, minute=0), id="auto_delete")

    scheduler.start()
    logger.info("[scheduler] Started. Jobs: " + ", ".join(j.id for j in scheduler.get_jobs()))

    # Startup scan
    logger.info("[scheduler] Running startup scan...")
    job_full_scan()

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("[scheduler] Stopped.")

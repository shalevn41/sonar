import logging
import time

from src.database.db import SessionLocal
from src.ai.groq_scorer import KeywordMatcher, GroqScorer
from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 80


def _get_scrapers(site: str | None = None) -> list[BaseScraper]:
    from src.scraper.alljobs import AllJobsScraper
    from src.scraper.drushim import DrushimScraper
    from src.scraper.gotfriends import GotFriendsScraper
    from src.scraper.jobmaster import JobMasterScraper
    from src.scraper.dialog import DialogScraper
    from src.scraper.jobnet import JobnetScraper

    all_scrapers = {
        "alljobs": AllJobsScraper,
        "drushim": DrushimScraper,
        "gotfriends": GotFriendsScraper,
        "jobmaster": JobMasterScraper,
        "dialog": DialogScraper,
        "jobnet": JobnetScraper,
    }

    if site:
        cls = all_scrapers.get(site.lower())
        return [cls()] if cls else []
    return [cls() for cls in all_scrapers.values()]


def run_scan(site: str | None = None, notify: bool = True):
    import os
    threshold = int(os.getenv("GROQ_SCORE_THRESHOLD", SCORE_THRESHOLD))

    matcher = KeywordMatcher()
    scorer = GroqScorer()
    db = SessionLocal()

    all_new_jobs = []
    high_score_jobs = []

    try:
        scrapers = _get_scrapers(site)
        for scraper in scrapers:
            start = time.time()
            logger.info(f"[runner] Scraping {scraper.source_name}...")
            try:
                raw_jobs = scraper.scrape()
            except Exception as e:
                logger.error(f"[runner] {scraper.source_name} failed: {e}")
                raw_jobs = []

            jobs_found = len(raw_jobs)
            jobs_new = 0
            new_job_objects = []

            for job in raw_jobs:
                if scraper.save_job(job, db):
                    jobs_new += 1
                    new_job_objects.append(job)

            # Score new jobs
            unscored = []
            for job in new_job_objects:
                if matcher.matches(job.get("title", ""), job.get("description", "")):
                    job["ai_score"] = 85
                    job["apply_priority"] = "high"
                    job["ai_reason"] = "Keyword match (Track 1)"
                else:
                    unscored.append(job)

            # Batch-score with Groq (Track 2)
            for i in range(0, len(unscored), 5):
                batch = unscored[i:i + 5]
                results = scorer.score_batch(batch)
                for job, result in zip(batch, results):
                    if result:
                        job["ai_score"] = result.get("score")
                        job["ai_reason"] = ", ".join(result.get("match_reasons", []))
                        job["ai_red_flags"] = ", ".join(result.get("red_flags", []))
                        job["ai_missing_skills"] = ", ".join(result.get("missing_skills", []))
                        job["apply_priority"] = result.get("apply_priority")

            # Update DB with scores
            from src.database.models import Job
            for job in new_job_objects:
                if job.get("ai_score") is not None:
                    db_job = db.query(Job).filter(Job.url == job["url"]).first()
                    if db_job:
                        db_job.ai_score = job["ai_score"]
                        db_job.ai_reason = job.get("ai_reason")
                        db_job.ai_red_flags = job.get("ai_red_flags")
                        db_job.ai_missing_skills = job.get("ai_missing_skills")
                        db_job.apply_priority = job.get("apply_priority")
                        db.commit()

                if (job.get("ai_score") or 0) >= threshold:
                    high_score_jobs.append(job)

            all_new_jobs.extend(new_job_objects)
            duration = time.time() - start
            scraper.log_scan(db, jobs_found, jobs_new, duration)

            # Stale site check
            if scraper.track_stale(jobs_found) and notify:
                from src.telegram.alerts import TelegramAlerter
                TelegramAlerter().send_stale_site_alert(scraper.source_name)

            logger.info(f"[runner] {scraper.source_name}: found={jobs_found} new={jobs_new} ({duration:.1f}s)")

        # Send immediate alerts for top 5 high-score jobs (avoid spam)
        if notify and high_score_jobs:
            from src.telegram.alerts import TelegramAlerter
            alerter = TelegramAlerter()
            top_alerts = sorted(high_score_jobs, key=lambda j: j.get("ai_score") or 0, reverse=True)[:5]
            for job in top_alerts:
                try:
                    alerter.send_immediate_alert(job)
                except Exception as e:
                    logger.error(f"[runner] Telegram alert failed: {e}")

        return all_new_jobs, high_score_jobs

    finally:
        db.close()

import hashlib
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.database.db import SessionLocal
from src.database.models import Job, ScanLog, RejectedCompany

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

_ua_index = 0
_stale_tracker: dict[str, int] = {}

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _load_json(filename: str) -> dict | list:
    with open(CONFIG_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class BaseScraper:
    source_name: str = "base"

    def __init__(self):
        self._blacklist: list[str] = [
            c.lower() for c in _load_json("blacklist.json").get("companies", [])
        ]
        self._search_terms: list[str] = _load_json("search_terms.json").get("terms", [])
        self._session = requests.Session()

    def _headers(self) -> dict:
        global _ua_index
        ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
        _ua_index += 1
        return {
            "User-Agent": ua,
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def get(self, url: str, retries: int = 3, **kwargs) -> requests.Response | None:
        for attempt in range(retries):
            try:
                resp = self._session.get(url, headers=self._headers(), timeout=15, **kwargs)
                resp.raise_for_status()
                return resp
            except Exception as e:
                wait = 2 ** attempt
                logger.warning(f"[{self.source_name}] GET {url} failed (attempt {attempt+1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
        logger.error(f"[{self.source_name}] All {retries} attempts failed for {url}")
        return None

    def is_duplicate(self, job_url: str, db: Session) -> bool:
        h = url_hash(job_url)
        return db.query(Job).filter(Job.url_hash == h).first() is not None

    def is_blacklisted(self, company: str) -> bool:
        if not company:
            return False
        return company.lower() in self._blacklist

    def is_too_old(self, date_posted: str | None) -> bool:
        """Return True if the job was posted more than 24 hours ago (best-effort)."""
        if not date_posted:
            return False
        text = date_posted.lower()
        # Definitely fresh
        fresh = ["היום", "today", "עכשיו", "just now", "דקות", "minutes",
                 "שעות", "hours", "שעה", "hour", "לפני"]
        for m in fresh:
            if m in text:
                return False
        # Definitely old
        old = ["אתמול", "yesterday", "ימים", "days", "שבוע", "week", "חודש", "month"]
        for m in old:
            if m in text:
                return True
        return False

    def save_job(self, job_dict: dict, db: Session) -> bool:
        """Save job to DB. Returns True if it's new."""
        job_url = job_dict.get("url", "")
        if not job_url:
            return False
        if self.is_duplicate(job_url, db):
            return False
        if self.is_blacklisted(job_dict.get("company", "")):
            logger.debug(f"[{self.source_name}] Blacklisted: {job_dict.get('company')}")
            return False

        job = Job(
            title=job_dict.get("title"),
            company=job_dict.get("company"),
            url=job_url,
            url_hash=url_hash(job_url),
            description=job_dict.get("description"),
            source=self.source_name,
            location=job_dict.get("location"),
            salary_range=job_dict.get("salary_range"),
            date_posted=job_dict.get("date_posted"),
            status="new",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return True

    def log_scan(self, db: Session, jobs_found: int, jobs_new: int, duration: float):
        entry = ScanLog(
            source=self.source_name,
            jobs_found=jobs_found,
            jobs_new=jobs_new,
            duration_seconds=round(duration, 2),
        )
        db.add(entry)
        db.commit()

    def track_stale(self, jobs_found: int) -> bool:
        """Returns True if this site is stale (0 results 3x in a row)."""
        if jobs_found == 0:
            _stale_tracker[self.source_name] = _stale_tracker.get(self.source_name, 0) + 1
        else:
            _stale_tracker[self.source_name] = 0
        return _stale_tracker.get(self.source_name, 0) >= 3

    def scrape(self) -> list[dict]:
        raise NotImplementedError

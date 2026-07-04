import logging
import os

from notion_client import Client

from src.database.db import SessionLocal
from src.database.models import Job

logger = logging.getLogger(__name__)


class NotionBackup:
    def __init__(self):
        self._client = Client(auth=os.getenv("NOTION_API_KEY"))
        self._db_id = os.getenv("NOTION_DB_ID", "")

    def backup_jobs(self):
        if not self._db_id:
            logger.warning("[notion] NOTION_DB_ID not set. Skipping backup.")
            return

        db = SessionLocal()
        try:
            jobs = db.query(Job).all()
            logger.info(f"[notion] Syncing {len(jobs)} jobs to Notion...")
            synced = 0
            for job in jobs:
                try:
                    self._upsert_job(job)
                    synced += 1
                except Exception as e:
                    logger.error(f"[notion] Failed to sync job {job.id}: {e}")
            logger.info(f"[notion] Backup complete. Synced: {synced}/{len(jobs)}")
        finally:
            db.close()

    def _upsert_job(self, job: Job):
        # Search for existing page by URL
        existing = self._client.databases.query(
            database_id=self._db_id,
            filter={"property": "URL", "url": {"equals": job.url or ""}},
        )

        props = {
            "Title": {"title": [{"text": {"content": job.title or ""}}]},
            "Company": {"rich_text": [{"text": {"content": job.company or ""}}]},
            "Score": {"number": job.ai_score},
            "Status": {"select": {"name": job.status or "new"}},
            "URL": {"url": job.url},
            "Source": {"rich_text": [{"text": {"content": job.source or ""}}]},
            "Location": {"rich_text": [{"text": {"content": job.location or ""}}]},
            "Priority": {"rich_text": [{"text": {"content": job.apply_priority or ""}}]},
        }

        if existing["results"]:
            page_id = existing["results"][0]["id"]
            self._client.pages.update(page_id=page_id, properties=props)
        else:
            self._client.pages.create(
                parent={"database_id": self._db_id},
                properties=props,
            )

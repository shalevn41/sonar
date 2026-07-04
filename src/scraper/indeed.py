import logging
import time
from xml.etree import ElementTree

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# RSS-based scraper — no Playwright needed, no anti-bot issues
RSS_BASE = "https://il.indeed.com/rss"


class IndeedScraper(BaseScraper):
    source_name = "indeed"

    def _parse_rss(self, xml_bytes: bytes) -> list[dict]:
        jobs = []
        try:
            root = ElementTree.fromstring(xml_bytes)
        except ElementTree.ParseError as e:
            logger.warning(f"[indeed] RSS parse error: {e}")
            return jobs

        channel = root.find("channel")
        if channel is None:
            return jobs

        for item in channel.findall("item"):
            title_raw = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            description = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()

            if not title_raw or not link:
                continue

            # Indeed RSS title format: "Job Title - Company Name"
            company = None
            title = title_raw
            if " - " in title_raw:
                parts = title_raw.rsplit(" - ", 1)
                title = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else None

            # Strip HTML tags from description
            import re
            description = re.sub(r"<[^>]+>", " ", description).strip()

            jobs.append({
                "title": title,
                "company": company,
                "url": link,
                "location": None,
                "salary_range": None,
                "description": description,
                "date_posted": pub_date or "היום",
            })

        return jobs

    def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        seen: set[str] = set()

        for term in self._search_terms[:12]:
            try:
                encoded = term.replace(" ", "+")
                url = f"{RSS_BASE}?q={encoded}&l=Israel&fromage=1&limit=25&sort=date"
                resp = self.get(url)
                if not resp:
                    continue

                for job in self._parse_rss(resp.content):
                    if job["url"] and job["url"] not in seen:
                        seen.add(job["url"])
                        all_jobs.append(job)

                time.sleep(1.5)
            except Exception as e:
                logger.error(f"[indeed] Error on term '{term}': {e}")

        logger.info(f"[indeed] Found {len(all_jobs)} jobs via RSS")
        return all_jobs

import logging
import time

from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.gotfriends.co.il"


class GotFriendsScraper(BaseScraper):
    source_name = "gotfriends"

    def _search_url(self, term: str) -> str:
        encoded = term.replace(" ", "+")
        return f"{BASE}/jobs/?q={encoded}"

    def _parse_jobs(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select("div.item, li.item"):
            try:
                link_el = card.select_one("a.position, a[class*='position']")
                if not link_el:
                    continue

                title = card.select_one("h2.title")
                title_text = title.get_text(strip=True) if title else link_el.get_text(strip=True)

                url = link_el.get("href", "")
                if url and not url.startswith("http"):
                    url = BASE + url

                # Location comes from span.info-data (first one = location)
                info_items = card.select("span.info-data")
                location = info_items[0].get_text(strip=True) if info_items else None

                # Description
                desc_el = card.select_one("div.desc, div.item_content")
                description = desc_el.get_text(strip=True) if desc_el else ""

                if not title_text or not url:
                    continue

                jobs.append({
                    "title": title_text,
                    "company": None,
                    "url": url,
                    "location": location,
                    "salary_range": None,
                    "date_posted": "היום",
                    "description": description,
                })
            except Exception as e:
                logger.debug(f"[gotfriends] Card parse error: {e}")

        return jobs

    def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        seen: set[str] = set()

        for term in self._search_terms[:15]:
            try:
                resp = self.get(self._search_url(term))
                if not resp:
                    continue
                for job in self._parse_jobs(resp.text):
                    if job["url"] and job["url"] not in seen:
                        seen.add(job["url"])
                        if not self.is_too_old(job.get("date_posted")):
                            all_jobs.append(job)
                time.sleep(1.2)
            except Exception as e:
                logger.error(f"[gotfriends] Error on term '{term}': {e}")

        logger.info(f"[gotfriends] Found {len(all_jobs)} unique jobs")
        return all_jobs

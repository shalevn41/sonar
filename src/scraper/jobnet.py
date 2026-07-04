import logging
import time

from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.jobnet.co.il"


class JobnetScraper(BaseScraper):
    source_name = "jobnet"

    def _search_url(self, term: str) -> str:
        encoded = term.replace(" ", "+")
        return f"{BASE}/jobs/?q={encoded}"

    def _parse_jobs(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select("div.inerwrap"):
            try:
                link_el = card.select_one("a[href*='positionid']")
                if not link_el:
                    continue

                title_el = card.select_one("div.titlehdn")
                title = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)

                url = link_el.get("href", "")
                if url and not url.startswith("http"):
                    url = BASE + url

                company_el = card.select_one("a[href*='Company'], a[href*='companyID'], p.company")
                company = company_el.get_text(strip=True) if company_el else None

                date_el = card.select_one("p.boxDateCls")
                date_posted = date_el.get_text(strip=True) if date_el else None

                desc_el = card.select_one("div.jobdesc, div.description, p.desc")
                description = desc_el.get_text(strip=True) if desc_el else ""

                if not title or not url:
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "url": url,
                    "location": None,
                    "salary_range": None,
                    "date_posted": date_posted,
                    "description": description,
                })
            except Exception as e:
                logger.debug(f"[jobnet] Card parse error: {e}")

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
                logger.error(f"[jobnet] Error on term '{term}': {e}")

        logger.info(f"[jobnet] Found {len(all_jobs)} unique jobs")
        return all_jobs

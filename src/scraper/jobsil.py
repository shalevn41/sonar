import logging
import time

from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class JobsIlScraper(BaseScraper):
    source_name = "jobsil"

    def _search_url(self, term: str) -> str:
        encoded = term.replace(" ", "+")
        return f"https://www.jobs.il/jobs/?q={encoded}"

    def _parse_jobs(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        jobs = []
        cards = soup.select(".job-item, .jobItem, article, [class*='job']")
        for card in cards:
            try:
                title_el = card.select_one("h2 a, h3 a, .title a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                url = title_el.get("href", "")
                if url and not url.startswith("http"):
                    url = "https://www.jobs.il" + url

                company_el = card.select_one(".company, .employer")
                company = company_el.get_text(strip=True) if company_el else None

                location_el = card.select_one(".location, .city")
                location = location_el.get_text(strip=True) if location_el else None

                date_el = card.select_one(".date, .posted")
                date_posted = date_el.get_text(strip=True) if date_el else None

                desc_el = card.select_one(".description, .summary")
                description = desc_el.get_text(strip=True) if desc_el else ""

                if not title or not url:
                    continue
                jobs.append({"title": title, "company": company, "url": url,
                             "location": location, "date_posted": date_posted,
                             "description": description, "salary_range": None})
            except Exception as e:
                logger.debug(f"[jobsil] Card parse error: {e}")
        return jobs

    def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        seen: set[str] = set()
        for term in self._search_terms[:12]:
            try:
                resp = self.get(self._search_url(term))
                if not resp:
                    continue
                for job in self._parse_jobs(resp.text):
                    if job["url"] and job["url"] not in seen:
                        seen.add(job["url"])
                        if not self.is_too_old(job.get("date_posted")):
                            all_jobs.append(job)
                time.sleep(1.5)
            except Exception as e:
                logger.error(f"[jobsil] Error on term '{term}': {e}")
        logger.info(f"[jobsil] Found {len(all_jobs)} unique jobs")
        return all_jobs

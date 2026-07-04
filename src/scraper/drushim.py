import logging
import time

from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.drushim.co.il"


class DrushimScraper(BaseScraper):
    source_name = "drushim"

    # cat4=הייטק-חומרה, cat5=הייטק-כללי, cat6=הייטק-תוכנה, cat2=בכירים/ניהול
    TECH_CATS = ["cat5", "cat6", "cat4", "cat2"]

    def _search_url(self, term: str, cat: str = "cat5") -> str:
        encoded = term.replace(" ", "+")
        return f"{BASE}/jobs/{cat}/?q={encoded}"

    def _parse_jobs(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select(".job-item"):
            try:
                title_el = card.select_one("span.job-url")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                link_el = card.select_one("a.no-underline[href*='/job/'], a[href*='/job/']")
                if not link_el:
                    continue
                url = link_el.get("href", "")
                if url and not url.startswith("http"):
                    url = BASE + url

                company_el = card.select_one("span.font-weight-medium.bidi, a.black--text")
                company = company_el.get_text(strip=True) if company_el else None

                location_el = card.select_one("div.flex.nowrap.flex-basis-0 span.display-18")
                location = location_el.get_text(strip=True).rstrip("|") if location_el else None

                date_el = card.select_one("span.display-18.inline-flex")
                date_posted = date_el.get_text(strip=True) if date_el else None

                desc_el = card.select_one("p.display-18.view-on-submit")
                description = desc_el.get_text(strip=True) if desc_el else ""

                if not title or not url:
                    continue
                jobs.append({
                    "title": title,
                    "company": company,
                    "url": url,
                    "location": location,
                    "salary_range": None,
                    "date_posted": date_posted,
                    "description": description,
                })
            except Exception as e:
                logger.debug(f"[drushim] Card parse error: {e}")

        return jobs

    def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        seen: set[str] = set()

        for cat in self.TECH_CATS:
            for term in self._search_terms[:10]:
                try:
                    resp = self.get(self._search_url(term, cat))
                    if not resp:
                        continue
                    for job in self._parse_jobs(resp.text):
                        if job["url"] and job["url"] not in seen:
                            seen.add(job["url"])
                            if not self.is_too_old(job.get("date_posted")):
                                all_jobs.append(job)
                    time.sleep(1.2)
                except Exception as e:
                    logger.error(f"[drushim] Error on {cat}/{term}: {e}")

        logger.info(f"[drushim] Found {len(all_jobs)} unique jobs")
        return all_jobs

import logging
import time

from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.jobmaster.co.il"


class JobMasterScraper(BaseScraper):
    source_name = "jobmaster"

    def _search_url(self, term: str) -> str:
        encoded = term.replace(" ", "+")
        return f"{BASE}/jobs/?q={encoded}"

    def _parse_jobs(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        jobs = []

        for card in soup.select(".JobItem"):
            try:
                link_el = card.select_one("a.CardHeader, a.View_Job_Details")
                if not link_el:
                    continue

                title = link_el.get_text(strip=True)
                url = link_el.get("href", "")
                if url and not url.startswith("http"):
                    url = BASE + "/" + url.lstrip("/")

                company_el = card.select_one("a.CompanyNameLink, span.CompanyName")
                company = company_el.get_text(strip=True) if company_el else None

                # Location is in a plain <span> inside JobExtraInfo (not in an <a> tag)
                location = None
                extra_el = card.select_one(".JobExtraInfo")
                if extra_el:
                    loc_span = extra_el.find("span", recursive=False) or extra_el.find("span")
                    if loc_span:
                        raw = loc_span.get_text(strip=True)
                        # Strip the work-type prefix if present (e.g. "עבודה מהבית, ראשון לציון")
                        if "," in raw:
                            location = raw.split(",")[-1].strip()
                        elif raw and not any(k in raw for k in ["מהבית", "היברידי", "מוגבלות", "דתי", "חרדי"]):
                            location = raw

                date_el = card.select_one("span.Gray")
                date_posted = date_el.get_text(strip=True) if date_el else None

                desc_el = card.select_one(".jobShortDescription")
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
                logger.debug(f"[jobmaster] Card parse error: {e}")

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
                logger.error(f"[jobmaster] Error on term '{term}': {e}")

        logger.info(f"[jobmaster] Found {len(all_jobs)} unique jobs")
        return all_jobs

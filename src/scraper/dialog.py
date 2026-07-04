import asyncio
import logging

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.dialog.co.il"

# dialog.co.il is a high-tech-only job board — search by sub-category pages
TECH_PATHS = [
    "/high-tech/jobs/software",
    "/high-tech/jobs/data",
    "/high-tech/jobs/system",
    "/high-tech/jobs/research",
]


class DialogScraper(BaseScraper):
    source_name = "dialog"

    def scrape(self) -> list[dict]:
        try:
            return asyncio.run(self._scrape_async())
        except Exception as e:
            logger.error(f"[dialog] Scrape failed: {e}")
            return []

    async def _scrape_async(self) -> list[dict]:
        from playwright.async_api import async_playwright

        all_jobs: list[dict] = []
        seen: set[str] = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="he-IL",
            )

            for path in TECH_PATHS:
                page = await context.new_page()
                try:
                    await page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(3)

                    content = await page.content()
                    if "captcha" in content.lower():
                        logger.warning("[dialog] Captcha detected. Skipping.")
                        await page.close()
                        break

                    jobs = await page.evaluate("""() => {
                        const results = [];
                        const cards = document.querySelectorAll(
                            'article, .job-item, .position-item, [class*="job"], [class*="position"], li.item'
                        );
                        cards.forEach(card => {
                            const link = card.querySelector('a[href*="/high-tech/jobs/"], a[href*="/job/"]');
                            if (!link) return;
                            const title = link.innerText.trim() || card.querySelector('h2,h3')?.innerText?.trim();
                            if (!title) return;
                            let url = link.href;
                            const company = card.querySelector('[class*="company"], [class*="employer"]')?.innerText?.trim() || null;
                            const location = card.querySelector('[class*="location"], [class*="city"]')?.innerText?.trim() || null;
                            const desc = card.querySelector('[class*="desc"], [class*="summary"], p')?.innerText?.trim() || '';
                            results.push({ title, url, company, location, description: desc, salary_range: null, date_posted: 'היום' });
                        });
                        return results;
                    }""")

                    for job in jobs:
                        if job.get("url") and job["url"] not in seen and job.get("title"):
                            seen.add(job["url"])
                            all_jobs.append(job)

                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"[dialog] Error on path '{path}': {e}")
                finally:
                    await page.close()

            await browser.close()

        logger.info(f"[dialog] Found {len(all_jobs)} jobs")
        return all_jobs

import asyncio
import logging

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.dialog.co.il"

# dialog.co.il is a high-tech-only job board — navigate by category pages
TECH_PATHS = [
    "/high-tech/jobs/software",
    "/high-tech/jobs/data",
    "/high-tech/jobs/system",
    "/high-tech/jobs/research",
    "/high-tech/jobs/product",
    "/high-tech/jobs/ai",
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
                extra_http_headers={"Accept-Language": "he-IL,he;q=0.9"},
            )

            for path in TECH_PATHS:
                page = await context.new_page()
                try:
                    await page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(3)

                    content = await page.content()
                    if "captcha" in content.lower():
                        logger.warning("[dialog] Captcha detected, stopping.")
                        await page.close()
                        break

                    # Log page structure for debugging if 0 results
                    jobs = await page.evaluate("""() => {
                        const out = [];
                        // Try all common card patterns dialog might use
                        const selectors = [
                            'article', '.job-item', '.position-item', '.job-card',
                            '[class*="job-item"]', '[class*="position-item"]', '[class*="JobItem"]',
                            'li.item', '.item', '[class*="card"]'
                        ];
                        let cards = [];
                        for (const sel of selectors) {
                            const found = document.querySelectorAll(sel);
                            if (found.length > 2) { cards = Array.from(found); break; }
                        }

                        cards.forEach(card => {
                            // Find the job link
                            const link = card.querySelector(
                                'a[href*="/high-tech/jobs/"], a[href*="/job/"], a[href*="position"], h2 a, h3 a, .title a'
                            );
                            if (!link) return;
                            const title = (link.innerText || link.textContent || '').trim();
                            if (!title || title.length < 3) return;
                            let url = link.href;
                            if (!url) return;

                            const company = (
                                card.querySelector('[class*="company"],[class*="employer"],[class*="Company"]')?.innerText ||
                                card.querySelector('[class*="logo"] img')?.alt || ''
                            ).trim() || null;

                            const location = (
                                card.querySelector('[class*="location"],[class*="city"],[class*="area"]')?.innerText || ''
                            ).trim() || null;

                            const desc = (
                                card.querySelector('[class*="desc"],[class*="summary"],[class*="text"],p')?.innerText || ''
                            ).trim();

                            out.push({ title, url, company, location, description: desc, date_posted: 'היום', salary_range: null });
                        });

                        // Debug: log how many cards were found
                        console.log('[dialog] cards found:', cards.length, 'on', window.location.pathname);
                        return out;
                    }""")

                    if jobs:
                        logger.info(f"[dialog] {path}: found {len(jobs)} job cards")
                    else:
                        # Log page structure to help debug
                        structure = await page.evaluate("""() => {
                            const tags = {};
                            document.querySelectorAll('*').forEach(el => {
                                const cls = el.className;
                                if (typeof cls === 'string' && cls.includes('job')) tags[cls] = (tags[cls]||0)+1;
                            });
                            return Object.keys(tags).slice(0, 20).join(' | ');
                        }""")
                        logger.warning(f"[dialog] {path}: 0 cards. Classes with 'job': {structure[:200]}")

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

        logger.info(f"[dialog] Total found: {len(all_jobs)} jobs")
        return all_jobs

import asyncio
import logging

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.alljobs.co.il"


class AllJobsScraper(BaseScraper):
    source_name = "alljobs"

    def scrape(self) -> list[dict]:
        try:
            return asyncio.run(self._scrape_async())
        except Exception as e:
            logger.error(f"[alljobs] Scrape failed: {e}")
            return []

    async def _scrape_async(self) -> list[dict]:
        from playwright.async_api import async_playwright

        all_jobs: list[dict] = []
        seen: set[str] = set()
        terms = self._search_terms[:10]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="he-IL",
            )

            for term in terms:
                page = await context.new_page()
                try:
                    encoded = term.replace(" ", "+")
                    url = f"{BASE}/SearchResultsGuest.aspx?page=1&position={encoded}&type=0&city=0&region=0&fromdate=1"
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)

                    # Wait for JS to render jobs
                    try:
                        await page.wait_for_selector(".cJobItem, [class*='job-content'], .job-result", timeout=8000)
                    except Exception:
                        pass
                    await asyncio.sleep(3)

                    content = await page.content()
                    if "captcha" in content.lower():
                        logger.warning("[alljobs] Captcha detected. Skipping.")
                        await page.close()
                        break

                    # Extract job cards
                    jobs = await page.evaluate("""() => {
                        const results = [];
                        // Try multiple selector patterns
                        const selectors = [
                            '.cJobItem', '.job-content', '[id*="job"]',
                            'article', '.result-item', '.job-item'
                        ];
                        let cards = [];
                        for (const sel of selectors) {
                            cards = document.querySelectorAll(sel);
                            if (cards.length > 0) break;
                        }
                        cards.forEach(card => {
                            const titleEl = card.querySelector('h2 a, h3 a, .job-title a, a.title, [class*="title"] a');
                            if (!titleEl) return;
                            const title = titleEl.innerText.trim();
                            let url = titleEl.href || titleEl.getAttribute('href') || '';
                            if (url && !url.startsWith('http')) url = 'https://www.alljobs.co.il' + url;
                            const companyEl = card.querySelector('[class*="company"], [class*="employer"]');
                            const locationEl = card.querySelector('[class*="location"], [class*="city"]');
                            const descEl = card.querySelector('[class*="desc"], [class*="summary"]');
                            results.push({
                                title, url,
                                company: companyEl ? companyEl.innerText.trim() : null,
                                location: locationEl ? locationEl.innerText.trim() : null,
                                description: descEl ? descEl.innerText.trim() : '',
                                date_posted: 'היום',
                                salary_range: null,
                            });
                        });
                        return results;
                    }""")

                    for job in jobs:
                        if job.get("url") and job["url"] not in seen and job.get("title"):
                            seen.add(job["url"])
                            all_jobs.append(job)

                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"[alljobs] Error on term '{term}': {e}")
                finally:
                    await page.close()

            await browser.close()

        logger.info(f"[alljobs] Found {len(all_jobs)} jobs")
        return all_jobs

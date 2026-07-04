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

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="he-IL",
                extra_http_headers={"Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8"},
            )
            await context.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

            for term in self._search_terms[:6]:
                page = await context.new_page()
                try:
                    # Load homepage where the search form lives
                    await page.goto(BASE, wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(3)

                    content = await page.content()
                    if "captcha" in content.lower():
                        logger.warning("[alljobs] Captcha on homepage, stopping.")
                        await page.close()
                        break

                    # Find the MUI Autocomplete / search input
                    search_input = await page.query_selector(
                        "input[placeholder*='תפקיד'], input[placeholder*='חפש'], "
                        "input[type='search'], .MuiInputBase-input, "
                        "[role='combobox'], input[name*='position'], input[name*='search']"
                    )
                    if not search_input:
                        logger.warning(f"[alljobs] Search input not found for '{term}'")
                        await page.close()
                        continue

                    await search_input.click()
                    await asyncio.sleep(0.5)
                    await search_input.fill(term)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")

                    # Wait for navigation to results page
                    await asyncio.sleep(5)

                    results_url = page.url
                    logger.debug(f"[alljobs] After search for '{term}': {results_url[:100]}")

                    content = await page.content()
                    if "captcha" in content.lower():
                        logger.warning("[alljobs] Captcha on results page, stopping.")
                        await page.close()
                        break

                    jobs = await page.evaluate("""() => {
                        const out = [];
                        const selectors = [
                            '.cJobItem','[class*="JobItem"]','[class*="job-item"]',
                            '[class*="job-content"]','[data-jobid]',
                            'article[class*="job"]','li[class*="job"]'
                        ];
                        let cards = [];
                        for (const sel of selectors) {
                            const found = document.querySelectorAll(sel);
                            if (found.length > 0) { cards = Array.from(found); break; }
                        }
                        console.log('[alljobs] cards:', cards.length, 'selector hit');
                        cards.forEach(card => {
                            const a = card.querySelector('h2 a,h3 a,a[href*="job"],a[href*="Job"],a[href*="position"]');
                            if (!a) return;
                            const title = (a.innerText||a.textContent||'').trim();
                            if (!title||title.length<3) return;
                            let url = a.href||'';
                            if (!url.startsWith('http')) url='https://www.alljobs.co.il'+url;
                            out.push({
                                title, url,
                                company: card.querySelector('[class*="company"],[class*="Company"],[class*="employer"]')?.innerText?.trim()||null,
                                location: card.querySelector('[class*="location"],[class*="city"],[class*="area"]')?.innerText?.trim()||null,
                                description: card.querySelector('[class*="desc"],[class*="snippet"],[class*="text"]')?.innerText?.trim()||'',
                                date_posted: card.querySelector('[class*="date"],[class*="time"]')?.innerText?.trim()||'היום',
                                salary_range: null,
                            });
                        });
                        return out;
                    }""")

                    if jobs:
                        logger.info(f"[alljobs] '{term}': {len(jobs)} cards")
                    else:
                        logger.warning(f"[alljobs] '{term}': 0 cards after form submit. URL={results_url[:80]}")

                    for job in jobs:
                        if job.get("url") and job["url"] not in seen and job.get("title"):
                            seen.add(job["url"])
                            all_jobs.append(job)

                except Exception as e:
                    logger.error(f"[alljobs] Error on term '{term}': {e}")
                finally:
                    await page.close()

                await asyncio.sleep(2)

            await browser.close()

        logger.info(f"[alljobs] Total: {len(all_jobs)} jobs")
        return all_jobs

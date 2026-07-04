import asyncio
import logging

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    source_name = "indeed"

    def scrape(self) -> list[dict]:
        try:
            return asyncio.run(self._scrape_async())
        except Exception as e:
            logger.error(f"[indeed] Scrape failed: {e}")
            return []

    async def _scrape_async(self) -> list[dict]:
        from playwright.async_api import async_playwright

        all_jobs: list[dict] = []
        seen: set[str] = set()
        terms = self._search_terms[:8]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="he-IL",
            )

            for term in terms:
                page = await context.new_page()
                try:
                    url = f"https://il.indeed.com/jobs?q={term.replace(' ', '+')}&fromage=1"
                    await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)

                    # Check for blocking
                    content = await page.content()
                    if "captcha" in content.lower() or "robot" in content.lower():
                        logger.warning("[indeed] Blocked by anti-bot. Skipping.")
                        await page.close()
                        break

                    cards = await page.query_selector_all("[data-jk], .job_seen_beacon, .tapItem")
                    for card in cards:
                        try:
                            title_el = await card.query_selector("h2 a, .jobTitle a")
                            if not title_el:
                                continue
                            title = await title_el.inner_text()
                            href = await title_el.get_attribute("href")
                            if not href:
                                continue
                            job_url = "https://il.indeed.com" + href if href.startswith("/") else href

                            if job_url in seen:
                                continue
                            seen.add(job_url)

                            company_el = await card.query_selector(".companyName, [data-testid='company-name']")
                            company = await company_el.inner_text() if company_el else None

                            location_el = await card.query_selector(".companyLocation, [data-testid='text-location']")
                            location = await location_el.inner_text() if location_el else None

                            salary_el = await card.query_selector(".salary-snippet, .estimated-salary")
                            salary = await salary_el.inner_text() if salary_el else None

                            snippet_el = await card.query_selector(".summary, .job-snippet")
                            description = await snippet_el.inner_text() if snippet_el else ""

                            all_jobs.append({
                                "title": title.strip(),
                                "company": company.strip() if company else None,
                                "url": job_url,
                                "location": location.strip() if location else None,
                                "salary_range": salary.strip() if salary else None,
                                "description": description.strip(),
                                "date_posted": "היום",
                            })
                        except Exception as e:
                            logger.debug(f"[indeed] Card parse error: {e}")

                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"[indeed] Error on term '{term}': {e}")
                finally:
                    await page.close()

            await browser.close()

        logger.info(f"[indeed] Found {len(all_jobs)} jobs")
        return all_jobs

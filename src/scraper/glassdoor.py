import asyncio
import logging

from src.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GlassdoorScraper(BaseScraper):
    source_name = "glassdoor"

    def scrape(self) -> list[dict]:
        try:
            return asyncio.run(self._scrape_async())
        except Exception as e:
            logger.error(f"[glassdoor] Scrape failed: {e}")
            return []

    async def _scrape_async(self) -> list[dict]:
        from playwright.async_api import async_playwright

        all_jobs: list[dict] = []
        seen: set[str] = set()
        terms = self._search_terms[:6]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="he-IL",
            )

            for term in terms:
                page = await context.new_page()
                try:
                    url = f"https://www.glassdoor.com/Job/israel-{term.replace(' ', '-').lower()}-jobs-SRCH_IL.0,6_IN119_KO7,{7+len(term)}.htm"
                    await page.goto(url, timeout=25000, wait_until="domcontentloaded")
                    await asyncio.sleep(3)

                    content = await page.content()
                    if "captcha" in content.lower() or "sign in" in content.lower():
                        logger.warning("[glassdoor] Login wall or captcha. Skipping.")
                        await page.close()
                        break

                    cards = await page.query_selector_all("[data-test='jobListing'], .react-job-listing, li.JobsList_jobListItem__JBBUV")
                    for card in cards:
                        try:
                            title_el = await card.query_selector("[data-test='job-title'], .JobCard_jobTitle__GLyJ1, a.jobLink")
                            if not title_el:
                                continue
                            title = await title_el.inner_text()
                            href = await title_el.get_attribute("href")
                            if not href:
                                continue
                            job_url = "https://www.glassdoor.com" + href if href.startswith("/") else href

                            if job_url in seen:
                                continue
                            seen.add(job_url)

                            company_el = await card.query_selector("[data-test='employer-name'], .EmployerProfile_compactEmployerName__9MGcV")
                            company = await company_el.inner_text() if company_el else None

                            location_el = await card.query_selector("[data-test='emp-location'], .JobCard_location__N_iYE")
                            location = await location_el.inner_text() if location_el else None

                            salary_el = await card.query_selector("[data-test='detailSalary'], .JobCard_salaryEstimate__arV5J")
                            salary = await salary_el.inner_text() if salary_el else None

                            all_jobs.append({
                                "title": title.strip(),
                                "company": company.strip() if company else None,
                                "url": job_url,
                                "location": location.strip() if location else None,
                                "salary_range": salary.strip() if salary else None,
                                "description": "",
                                "date_posted": "היום",
                            })
                        except Exception as e:
                            logger.debug(f"[glassdoor] Card parse error: {e}")

                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"[glassdoor] Error on term '{term}': {e}")
                finally:
                    await page.close()

            await browser.close()

        logger.info(f"[glassdoor] Found {len(all_jobs)} jobs")
        return all_jobs

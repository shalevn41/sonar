import json
import logging
import os
import time
from pathlib import Path

from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _load_json(filename: str) -> dict | list:
    with open(CONFIG_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


class KeywordMatcher:
    def __init__(self):
        data = _load_json("keywords.json")
        all_terms = data.get("english", []) + data.get("hebrew", [])
        self._keywords = [k.lower() for k in all_terms]

    def matches(self, title: str, description: str = "") -> bool:
        text = (title + " " + description).lower()
        return any(kw in text for kw in self._keywords)


class GroqScorer:
    def __init__(self):
        self._client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self._model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        profile = _load_json("profile.json")
        self._prompt = profile["groq_prompt"]

    def score_batch(self, jobs: list[dict]) -> list[dict]:
        """Score up to 5 jobs in one Groq call. Returns list of score dicts."""
        if not jobs:
            return []

        jobs_payload = json.dumps(
            [{"title": j.get("title", ""), "company": j.get("company", ""),
              "description": (j.get("description") or "")[:800],
              "location": j.get("location", ""), "salary": j.get("salary_range", "")}
             for j in jobs],
            ensure_ascii=False
        )

        for wait in [0, 10, 30, 60]:
            if wait:
                logger.warning(f"[groq] Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": self._prompt},
                        {"role": "user", "content": jobs_payload},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )
                raw = response.choices[0].message.content.strip()
                results = json.loads(raw)
                if isinstance(results, dict):
                    results = [results]
                return results
            except RateLimitError:
                continue
            except json.JSONDecodeError as e:
                logger.error(f"[groq] JSON parse error: {e}. Raw: {raw[:200]}")
                return [None] * len(jobs)
            except Exception as e:
                logger.error(f"[groq] Unexpected error: {e}")
                return [None] * len(jobs)

        logger.error("[groq] All retries exhausted.")
        return [None] * len(jobs)

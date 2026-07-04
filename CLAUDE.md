# CLAUDE.md — Sonar Project Context

> Read this file at the start of every session. This is the single source of truth.
> Do not assume anything that is not written here.

---

## 1. Project Identity

- **Name:** Sonar (formerly: job-hunter-bot, Smart Job Tracker)
- **Owner:** Noam Shalev (shalevn41@gmail.com | noamwork358@gmail.com)
- **GitHub:** https://github.com/shalevn41/sonar
- **Purpose:** Personal automated job-hunting system — scrapes 9 Israeli job sites, scores jobs with AI, sends alerts via Telegram
- **Current use:** Personal only (not public-facing yet)
- **Apple Developer Account:** Approved ($99/year) — for future iOS build

---

## 2. BUILD STRATEGY — TWO PHASES

### Phase A (CURRENT — Build This First)
**Python script + Telegram alerts. No mobile app yet.**

Goal: Get a working scraper + AI scorer + Telegram notifications running within 1-2 weeks.
Run it for a full month, tune keywords and Groq prompt with real data.
Only after Phase A is stable → move to Phase B.

### Phase B (FUTURE — After Phase A is proven)
**Full mobile app:** React Native + Expo + NativeWind + FastAPI REST API.
Design inspiration: Nixtio/Crextio (Dribbble) — warm, clean, human aesthetic.
Do NOT build Phase B components until Phase A is working and validated.

---

## 3. Full Tech Stack

### Phase A (Backend — build now)
| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.11 |
| Scraping (standard) | requests + BeautifulSoup4 | latest |
| Scraping (heavy) | Playwright | 1.40 |
| AI Scoring | Groq `openai/gpt-oss-120b` | — |
| Database | PostgreSQL | 15 |
| ORM | SQLAlchemy | 2.0 |
| Scheduler | APScheduler | 3.10 |
| Alerts | python-telegram-bot | 20.7 |
| Backup | Notion API | 2.2 |
| CLI output | Rich | 13.7 |
| Deploy | Railway Pro ($20/month) | — |

### Phase B (Mobile — future)
| Layer | Technology |
|---|---|
| Mobile Frontend | React Native + Expo + TypeScript |
| Styling | NativeWind (Tailwind for RN) |
| Animations | Reanimated / Framer Motion |
| Charts | Victory Native |
| Notifications | Expo Push Notifications |
| API | FastAPI + Uvicorn + API Key auth |
| Build | EAS Build |

---

## 4. System Architecture

```
[9 Job Sites]
      ↓
 Scraper Layer
 (Python, Sequential, 09:00 / 13:00 / 17:00 + Startup Scan)
      ↓
 Dedup Engine (SHA256 hash of URL)
      ↓
 Blacklist Filter (company names to exclude)
      ↓
 Track 1 — Keyword Match (~120 terms)
 → match: score 85+ → save to DB → Telegram alert
 → no match: send to Track 2
      ↓
 Track 2 — Groq AI (openai/gpt-oss-120b)
 Batch of 5 jobs, JSON output
      ↓
 PostgreSQL DB
      ↓
 Telegram Alerts (immediate if score > 80, daily summary at 09:00)
 +
 Notion Backup (daily at 00:00)
```

### Phase B adds on top:
```
PostgreSQL DB
      ↓
 FastAPI (REST + API Key auth)
      ↓
 React Native App (Expo + NativeWind)
 iOS + Android
 +
 Expo Push Notifications
```

---

## 5. Job Sites to Scrape

| Site | Method | Schedule |
|---|---|---|
| AllJobs | requests + BS4 | 09:00, 13:00, 17:00 |
| Drushim | requests + BS4 | 09:00, 13:00, 17:00 |
| GotFriends | requests + BS4 | 09:00, 13:00, 17:00 |
| JobMaster | requests + BS4 | 09:00, 13:00, 17:00 |
| Dialog | requests + BS4 | 09:00, 13:00, 17:00 |
| Jobs.il | requests + BS4 | 09:00, 13:00, 17:00 |
| Jobnet | requests + BS4 | 09:00, 13:00, 17:00 |
| Indeed | Playwright | 09:30 (separate run) |
| Glassdoor | Playwright | 09:30 (separate run) |

**Stale site alert:** If a site returns 0 results for 3 consecutive scans → send Telegram warning.

---

## 6. File Structure

### Phase A (current)
```
sonar/
├── .env                    ← secrets (never commit)
├── .env.example            ← template with empty values (commit this)
├── .gitignore
├── requirements.txt
├── README.md
├── Procfile                ← for Railway: "web: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT"
├── CLAUDE.md               ← this file
├── main.py                 ← CLI entry point (python main.py scan/list/top/stats)
│
├── src/
│   ├── __init__.py
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── base_scraper.py     ← headers, retry logic, dedup, blacklist, 24h filter
│   │   ├── alljobs.py
│   │   ├── drushim.py
│   │   ├── gotfriends.py
│   │   ├── jobmaster.py
│   │   ├── dialog.py
│   │   ├── jobsil.py
│   │   ├── jobnet.py
│   │   ├── indeed.py           ← Playwright
│   │   └── glassdoor.py        ← Playwright
│   ├── ai/
│   │   └── groq_scorer.py      ← openai/gpt-oss-120b, batch of 5, JSON output
│   ├── database/
│   │   ├── db.py               ← SQLAlchemy connection
│   │   └── models.py           ← 3 tables: jobs, scan_log, rejected_companies
│   ├── scheduler/
│   │   └── jobs.py             ← APScheduler: 09:00, 09:30, 13:00, 17:00, 00:00
│   ├── telegram/
│   │   └── alerts.py           ← bot alerts + /top10 /scan /stats commands
│   └── notion/
│       └── backup.py           ← nightly backup at 00:00
│
├── config/
│   ├── keywords.json           ← Track 1 (~120 keywords, Hebrew + English)
│   ├── search_terms.json       ← search queries for scrapers (~65 terms)
│   ├── blacklist.json          ← companies to skip
│   └── profile.json            ← Noam's profile for Groq prompt
│
└── logs/
    ├── app.log
    └── error.log
```

### Phase B adds:
```
sonar/
├── src/
│   └── api/
│       ├── main.py             ← FastAPI + API Key auth middleware
│       └── push_tokens.py      ← Expo push token registration
│
└── mobile/
    ├── app.json
    ├── package.json
    ├── tailwind.config.js
    ├── App.tsx
    ├── navigation/
    │   └── BottomTabs.tsx
    ├── screens/
    │   ├── JobsScreen.tsx
    │   ├── AnalyticsScreen.tsx
    │   └── ConfigScreen.tsx
    ├── components/
    │   ├── JobCard.tsx
    │   ├── ExpandedCard.tsx
    │   ├── StatCard.tsx
    │   └── FilterBar.tsx
    └── utils/
        ├── api.ts
        └── notifications.ts
```

---

## 7. Database Schema

### Table: jobs (20 columns)
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | auto |
| title | TEXT | job title |
| company | TEXT | company name |
| url | TEXT UNIQUE | direct link |
| url_hash | TEXT UNIQUE | SHA256 for dedup |
| description | TEXT | full description |
| source | TEXT | alljobs/drushim/etc |
| location | TEXT | city/area |
| salary_range | TEXT | salary if listed |
| date_found | TIMESTAMP | when scraped |
| date_posted | TEXT | original post date |
| ai_score | INTEGER | 0-100 from Groq |
| ai_reason | TEXT | why this score |
| ai_red_flags | TEXT | warnings |
| ai_missing_skills | TEXT | skill gaps |
| apply_priority | TEXT | high/medium/low |
| status | TEXT | new/viewed/saved/applied/interview/rejected |
| company_rejected_me | BOOLEAN | red badge |
| notes | TEXT | personal notes |
| applied_date | TIMESTAMP | when CV sent |

### Table: scan_log
| Column | Type |
|---|---|
| id | INTEGER PK |
| scan_date | TIMESTAMP |
| source | TEXT |
| jobs_found | INTEGER |
| jobs_new | INTEGER |
| duration_seconds | FLOAT |

### Table: rejected_companies
| Column | Type |
|---|---|
| id | INTEGER PK |
| company_name | TEXT |

---

## 8. Auto-Delete Rules

| Score | Status | Delete after |
|---|---|---|
| 0-60 | new / viewed | 7 days |
| 60+ | new / viewed | 30 days |
| any | applied / saved / interview | never |

---

## 9. Scheduler Timetable

| Time | Action |
|---|---|
| Startup | Initial scan (all 7 BS4 sites) |
| 09:00 | Full scan + morning summary Telegram |
| 09:30 | Indeed + Glassdoor (Playwright, separate) |
| 13:00 | Full scan |
| 17:00 | Final daily scan |
| 00:00 | Notion backup |

---

## 10. Groq Scoring (openai/gpt-oss-120b)

### Model
- Model: `openai/gpt-oss-120b`
- Batch size: 5 jobs per request
- Output: JSON only
- Fallback: if score=null → retry on next scan
- Backoff: 10s → 30s → 60s on rate limit

### Prompt (profile.json)
```
אתה מערכת סקורינג משרות עבור נועם שלו, בן 25.

כישורים: n8n, Make, Zapier, Python, Groq, OpenAI, Claude, Gemini,
Tavily, MongoDB, MySQL, Qdrant, PostgreSQL, Redis, Supabase, Docker,
Railway, Git, GitHub, SQLAlchemy, APScheduler, React Native, Expo,
Base44, Bolt.new, Cursor, Claude Code, Replit, RAG, LangChain,
Multi-Agent, Airtable, REST APIs, Webhooks, BeautifulSoup,
Playwright, FastAPI.

רקע: ניהול סניף (Anifit), לוגיסטיקה, לקוחות עסקיים (UPS).

תחומים רלוונטיים: AI/Automation, Tech, Operations+AI,
Business+AI, Startup, Product+AI, Data+AI, ממשלה דיגיטלית,
לוגיסטיקה+טכנולוגיה. לא מסנן לפי שנות ניסיון.

החזר JSON בלבד:
{
  "score": 0-100,
  "match_reasons": ["סיבה 1", "סיבה 2"],
  "red_flags": ["דגל אדום"],
  "missing_skills": ["כישור חסר"],
  "salary_fit": true/false,
  "apply_priority": "high/medium/low"
}
```

### Track 1 — Keyword categories (~120 terms)
Covers: AI, automation, no-code, n8n, Make, Zapier, Python, LLM, GPT, Claude,
agents, RAG, LangChain, data pipelines, ETL, workflow, integration,
operations manager, process automation, RevOps, growth, tech lead,
product manager tech, CTO, startup, scaleup, logistics tech.

---

## 11. Telegram Bot

- Bot name: @noam_radar_bot
- Immediate alert: score > 80
- Morning summary: 09:00 daily
- Commands: /top10, /scan, /stats

### Message formats

**Immediate alert (score > 80):**
```
🎯 משרה חדשה! ציון: 87/100
תפקיד: AI Automation Engineer
חברה: TechStartup
מיקום: תל אביב | שכר: 18,000-22,000 ₪
למה מתאים: דורש n8n, Python, automation
Red flags: דרוש תואר ראשון
🔗 [פתח משרה]
```

**Morning summary:**
```
☀️ סיכום בוקר - DD/MM/YYYY
נסרקו: 847 | חדשות: 23 | מעל 80: 4

Top 3 היום:
1. AI Engineer - TechCo (92/100)
2. Automation Specialist - StartupX (85/100)
3. RevOps Manager - ScaleUp (81/100)
```

**Zero results above 80:**
```
סיכום בוקר - DD/MM/YYYY
אין משרות חדשות מעל 80 הלילה.
נסרקו: 312 | חדשות: 8 | הכי גבוה: 71/100
```

**Stale site alert:**
```
⚠️ sonar alert
AllJobs לא החזיר תוצאות ב-3 סריקות רצופות.
ייתכן שהאתר השתנה — בדוק את ה-scraper.
```

---

## 12. CLI Commands (main.py)

```bash
python main.py scan      # manual scan now
python main.py list      # last 20 jobs
python main.py top       # top 10 by score
python main.py stats     # scan statistics
```

---

## 13. Environment Variables (.env)

```
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
API_SECRET_KEY=           # random string, protects API in Phase B
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DATABASE_URL=postgresql://postgres:password@localhost:5432/sonar
NOTION_API_KEY=
NOTION_DB_ID=
SCAN_TIMES=09:00,13:00,17:00
GROQ_SCORE_THRESHOLD=80
```

---

## 14. External Accounts

| Service | Status | Notes |
|---|---|---|
| GitHub | Active (shalevn41) | repo: github.com/shalevn41/sonar |
| Railway Pro | $20/month | backend deploy |
| Groq | Free API Key | console.groq.com |
| Telegram | Bot token exists | from job-hunter-bot |
| Notion | Integration connected | secret_... |
| Apple Developer | Approved | $99/year, for Phase B iOS |
| Expo | Free account | for Phase B EAS Build |

---

## 15. Phase A Build Steps

| Step | What | Time |
|---|---|---|
| 0 | Environment setup + venv + .env + GitHub push | 30 min |
| 1 | PostgreSQL + SQLAlchemy models (3 tables) | 1-2 hrs |
| 2 | base_scraper.py + AllJobs scraper | 2-3 hrs |
| 3 | Groq AI scorer (Track 1 + Track 2) | 2 hrs |
| 4 | Telegram alerts + bot commands | 1-2 hrs |
| 5 | APScheduler (all timetable entries) | 1 hr |
| 6 | Remaining 5 BS4 scrapers | 3-4 hrs |
| 7 | Indeed + Glassdoor (Playwright) | 3-4 hrs |
| 8 | CLI (Rich) + Notion backup | 1-2 hrs |
| 9 | Deploy to Railway | 1-2 hrs |

**Total Phase A: ~15-20 hours**

---

## 16. Phase B Build Steps (future)

| Step | What | Time |
|---|---|---|
| 10 | FastAPI + API Key auth + all endpoints | 1-2 hrs |
| 11 | Expo React Native init + NativeWind + navigation | 2-3 hrs |
| 12 | Jobs / Analytics / Config screens | 6-8 hrs |
| 13 | EAS Build + iOS/Android install | 2-3 hrs |

---

## 17. Phase B — Mobile UI Spec (for future reference)

**Design system:**
- Background: `linear-gradient(135deg, #f8f7f2, #fdf9e8, #faf5d0)`
- Cards: `rgba(255,255,255,0.85)` with `0.5px solid rgba(220,215,200,0.5)` border
- Accent primary: `#1a1a1a` (black)
- Accent secondary: `#f5c842` (warm yellow)
- Text primary: `#1a1a1a` / secondary: `#888888`
- Font: Inter
- Border radius: 12-16px
- Inspiration: Nixtio/Crextio on Dribbble

**Navigation:** Bottom Tab Bar — Jobs (with unviewed badge) / Analytics / Config

**Jobs screen:** 4 stat cards, job list with tap-to-expand, search, filters, sort, Export (Share Sheet), "Open Job" via Linking.openURL

**Analytics screen:** Line chart (jobs/day), Pie (status breakdown), Bar (avg score by source), Top 5 companies, conversion rate

**Config screen:** Keywords editor, blacklist, active sites toggles, Groq prompt editor, Telegram settings, Scan Now button

**Phase B FastAPI endpoints:**
- `GET /api/jobs` — with filters, requires `X-API-Key` header
- `GET /api/jobs/{id}`
- `PATCH /api/jobs/{id}/status`
- `GET /api/stats`
- `POST /api/scan`
- `GET/PUT /api/config`
- `DELETE /api/jobs/{id}`
- `POST /api/push-token` — registers device for push notifications

---

## 18. Mandatory Working Rules

1. **Read every line of AI-generated code before continuing** — no exceptions
2. **Report problems immediately** — never hide errors or gloss over them
3. **Explain every new file** — what it does, what it connects to
4. **Verify each step works before starting the next**
5. **Never mix Phase A and Phase B** — build Phase A completely first
6. **All secrets go in .env** — never hardcode keys in source files
7. **Always activate venv before running anything:** `source venv/bin/activate`
8. **Development environment:** MacBook Air M4, Cursor IDE, Claude Code CLI in integrated terminal

---

## 19. Current Status

**Phase A:** Not started — ready to begin from Step 0.
**Phase B:** Planned, not started.

> Update this section at the end of every session with what was completed.

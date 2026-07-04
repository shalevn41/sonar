# Sonar

Automated job-hunting system — scrapes 9 Israeli job sites, scores jobs with Groq AI, sends alerts via Telegram.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # fill in your keys
python main.py initdb
```

## Usage

```bash
python main.py scan    # manual scan
python main.py list    # last 20 jobs
python main.py top     # top 10 by score
python main.py stats   # scan statistics
python main.py         # start scheduler (production)
```

import sys
import os
from dotenv import load_dotenv

load_dotenv()


def cmd_initdb():
    from src.database.db import init_db
    init_db()
    from rich.console import Console
    Console().print("[green]✓ Database tables created.[/green]")


def cmd_scan(site=None):
    from src.scraper.runner import run_scan
    run_scan(site=site)


def cmd_list():
    from src.cli.display import show_recent
    show_recent()


def cmd_top():
    from src.cli.display import show_top
    show_top()


def cmd_stats():
    from src.cli.display import show_stats
    show_stats()


def cmd_score_test():
    from src.ai.groq_scorer import GroqScorer
    from rich.console import Console
    console = Console()
    scorer = GroqScorer()
    test_jobs = [
        {
            "title": "AI Automation Engineer",
            "company": "TechStartup",
            "description": "We need someone with n8n, Python, LangChain, and Groq experience to build AI workflows.",
            "location": "תל אביב",
            "salary_range": "20,000-25,000 ₪",
        },
        {
            "title": "Junior Accountant",
            "company": "Finance Corp",
            "description": "Looking for a junior accountant with Excel experience.",
            "location": "ירושלים",
            "salary_range": "8,000-10,000 ₪",
        },
    ]
    console.print("[cyan]Running Groq scorer on 2 test jobs...[/cyan]")
    results = scorer.score_batch(test_jobs)
    import json
    console.print_json(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_start():
    from src.scheduler.jobs import start_scheduler
    start_scheduler()


def print_help():
    print("""
Sonar — Job Tracker CLI

Commands:
  python main.py initdb       Create database tables
  python main.py scan         Run a manual scan (all sites)
  python main.py scan alljobs Scan specific site
  python main.py list         Show last 20 jobs
  python main.py top          Show top 10 jobs by score
  python main.py stats        Show scan statistics
  python main.py score --test Test Groq scorer
  python main.py              Start scheduler (production)
""")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        cmd_start()
    elif args[0] == "initdb":
        cmd_initdb()
    elif args[0] == "scan":
        site = args[1] if len(args) > 1 else None
        cmd_scan(site=site)
    elif args[0] == "list":
        cmd_list()
    elif args[0] == "top":
        cmd_top()
    elif args[0] == "stats":
        cmd_stats()
    elif args[0] == "score" and len(args) > 1 and args[1] == "--test":
        cmd_score_test()
    elif args[0] in ("--help", "-h", "help"):
        print_help()
    else:
        print(f"Unknown command: {args[0]}")
        print_help()
        sys.exit(1)

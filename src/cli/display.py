from rich.console import Console
from rich.table import Table
from rich import box

from src.database.db import SessionLocal
from src.database.models import Job, ScanLog
from sqlalchemy import func

console = Console()


def _score_color(score: int | None) -> str:
    if score is None:
        return "dim"
    if score >= 80:
        return "green bold"
    if score >= 60:
        return "yellow"
    return "red"


def show_recent(limit: int = 20):
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.date_found.desc()).limit(limit).all()
        if not jobs:
            console.print("[yellow]No jobs found in database.[/yellow]")
            return

        table = Table(title=f"Last {limit} Jobs", box=box.ROUNDED, show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Score", width=7)
        table.add_column("Title", min_width=25)
        table.add_column("Company", min_width=18)
        table.add_column("Location", min_width=12)
        table.add_column("Source", width=10)
        table.add_column("Status", width=10)
        table.add_column("Found", width=12)

        for i, j in enumerate(jobs, 1):
            score_str = str(j.ai_score) if j.ai_score is not None else "—"
            color = _score_color(j.ai_score)
            found = j.date_found.strftime("%d/%m %H:%M") if j.date_found else "—"
            table.add_row(
                str(i),
                f"[{color}]{score_str}[/{color}]",
                j.title or "—",
                j.company or "—",
                j.location or "—",
                j.source or "—",
                j.status or "—",
                found,
            )

        console.print(table)
    finally:
        db.close()


def show_top(limit: int = 10):
    db = SessionLocal()
    try:
        jobs = (
            db.query(Job)
            .filter(Job.ai_score.isnot(None))
            .order_by(Job.ai_score.desc())
            .limit(limit)
            .all()
        )
        if not jobs:
            console.print("[yellow]No scored jobs found.[/yellow]")
            return

        table = Table(title=f"Top {limit} Jobs by Score", box=box.ROUNDED, show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Score", width=7)
        table.add_column("Title", min_width=25)
        table.add_column("Company", min_width=18)
        table.add_column("Location", min_width=12)
        table.add_column("Priority", width=10)
        table.add_column("URL", min_width=30)

        for i, j in enumerate(jobs, 1):
            color = _score_color(j.ai_score)
            table.add_row(
                str(i),
                f"[{color}]{j.ai_score}[/{color}]",
                j.title or "—",
                j.company or "—",
                j.location or "—",
                j.apply_priority or "—",
                j.url or "—",
            )

        console.print(table)
    finally:
        db.close()


def show_stats():
    db = SessionLocal()
    try:
        total_jobs = db.query(Job).count()
        scored_jobs = db.query(Job).filter(Job.ai_score.isnot(None)).count()
        above_80 = db.query(Job).filter(Job.ai_score >= 80).count()
        avg_score = db.query(func.avg(Job.ai_score)).scalar()
        total_scans = db.query(ScanLog).count()

        # Per-source breakdown
        sources = db.query(ScanLog.source, func.sum(ScanLog.jobs_found), func.sum(ScanLog.jobs_new)).group_by(ScanLog.source).all()

        console.print("\n[bold cyan]Sonar Statistics[/bold cyan]")
        console.print(f"  Total jobs in DB:   [bold]{total_jobs}[/bold]")
        console.print(f"  Scored jobs:        [bold]{scored_jobs}[/bold]")
        console.print(f"  Jobs scoring ≥80:   [bold green]{above_80}[/bold green]")
        console.print(f"  Average score:      [bold]{f'{avg_score:.1f}' if avg_score else '—'}[/bold]")
        console.print(f"  Total scans run:    [bold]{total_scans}[/bold]")

        if sources:
            table = Table(title="Scans by Source", box=box.SIMPLE)
            table.add_column("Source", min_width=15)
            table.add_column("Total Found", justify="right")
            table.add_column("New Jobs", justify="right")
            for source, found, new in sources:
                table.add_row(source or "—", str(int(found or 0)), str(int(new or 0)))
            console.print(table)

    finally:
        db.close()

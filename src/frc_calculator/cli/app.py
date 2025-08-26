from __future__ import annotations

import argparse
import json
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.status import Status
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn

from frc_calculator.models.event import Event
from frc_calculator.services.season import Season


def cmd_analyze_event(args: argparse.Namespace) -> int:
    console = Console()
    status = console.status(
        f"Fetching {args.season} {args.event}: teams, rankings, alliances, matches, awards...",
        spinner="dots",
    )
    def on_progress(msg: str):
        try:
            status.update(f"{msg} ...")
        except Exception:
            pass
    with status:
        event = Event(args.season, args.event, progress=on_progress)
    console = Console()
    table = Table(title=f"Event {args.season} {args.event}")
    table.add_column("Team")
    table.add_column("Rank")
    table.add_column("Alliance")
    for team in event.teams.values():
        alliance = team.alliance.allianceNumber if team.alliance else "-"
        table.add_row(str(team.teamNumber), str(team.ranking), str(alliance))
    console.print(table)
    return 0


def cmd_calculate_points(args: argparse.Namespace) -> int:
    event = Event(args.season, args.event)
    team = event.get_team_from_number(args.team)
    points = team.regional_points_2025()
    if args.json:
        print(json.dumps({"team": team.teamNumber, "points": points}))
    else:
        if args.verbose:
            team.verbose_regional_points_2025()
        else:
            print(f"Team {team.teamNumber} points: {points}")
    return 0


def cmd_regional_pool(args: argparse.Namespace) -> int:
    console = Console()
    # Pre-count events to display a progress bar (listing is cheap; building events is the heavy part)
    try:
        from frc_calculator.data.frc_events import request_event_listings
        listings = request_event_listings(args.season)
        total_events = sum(len(listings[f"Week {w}"]["Events"]) for w in [1,2,3,4,5,6])
    except Exception:
        total_events = 0

    def build_season_with_progress():
        if total_events <= 0:
            # Fallback to simple spinner
            with console.status("Building season (this may take a while)...", spinner="dots"):
                return Season(args.season, useSeason=args.use_season)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("Building events"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("build", total=total_events)
                def on_event_built(_event_code: str):
                    try:
                        progress.advance(task)
                    except Exception:
                        pass
                return Season(args.season, useSeason=args.use_season, progress=on_event_built)

    season = build_season_with_progress()
    pool = season.regional_pool_2025(weekNumber=args.week)
    if args.json:
        serial = {}
        for rank, row in pool.items():
            serial[rank] = {
                "team": row["team"].teamNumber,
                "points": row["points"],
                "qualified": row["qualified"],
            }
        print(json.dumps(serial, indent=2))
    else:
        console = Console()
        table = Table(title=f"Regional Pool week {args.week} (useSeason={args.use_season})")
        table.add_column("Rank")
        table.add_column("Team")
        table.add_column("Points")
        table.add_column("Qualified")
        for rank, row in list(pool.items())[: args.top or len(pool)]:
            table.add_row(
                str(rank),
                str(row["team"].teamNumber),
                str(row["points"][0]),
                str(row["qualified"]["isQualified"]),
            )
        console.print(table)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="frc-calculator")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze-event", help="Analyze an event teams and alliances")
    a.add_argument("season", type=int)
    a.add_argument("event")
    a.set_defaults(func=cmd_analyze_event)

    c = sub.add_parser("calculate-points", help="Calculate regional points for a team")
    c.add_argument("season", type=int)
    c.add_argument("event")
    c.add_argument("team", type=int)
    c.add_argument("--verbose", action="store_true")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_calculate_points)

    r = sub.add_parser("regional-pool", help="Show regional pool standings")
    r.add_argument("season", type=int)
    r.add_argument("--use-season", type=int, default=None, help="Rules season to use")
    r.add_argument("--week", type=int, default=6)
    r.add_argument("--top", type=int, default=0)
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_regional_pool)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # default useSeason equals season if not provided
    if getattr(args, "use_season", None) is None and args.cmd == "regional-pool":
        args.use_season = args.season
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

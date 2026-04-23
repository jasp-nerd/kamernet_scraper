"""Command-line entry point: `python -m radar`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from radar import __version__
from radar.config import load_settings
from radar.db import Database
from radar.notify import build_notifiers
from radar.profile import PROFILES_DIR, load_profile
from radar.scheduler import Radar

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s · %(message)s",
        datefmt="%H:%M:%S",
    )


def _cmd_init_db(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.database_url:
        print("error: DATABASE_URL is not set", file=sys.stderr)
        return 1
    if not SCHEMA_PATH.exists():
        print(f"error: schema file not found at {SCHEMA_PATH}", file=sys.stderr)
        return 1
    db = Database(settings.database_url)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    print(f"running {SCHEMA_PATH} against {settings.database_url.rsplit('@', 1)[-1]}")
    db.init_schema(schema_sql)
    db.close()
    print("schema initialized ✓")
    return 0


def _cmd_list_profiles(args: argparse.Namespace) -> int:
    profiles = sorted(PROFILES_DIR.glob("*.yaml"))
    if not profiles:
        print(f"no profiles found in {PROFILES_DIR}")
        return 1
    print(f"profiles in {PROFILES_DIR}:")
    for path in profiles:
        try:
            p = load_profile(path.stem)
            print(f"  • {p.name:<35} {p.description}")
        except Exception as exc:
            print(f"  ! {path.stem:<35} (load error: {exc})")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    settings = load_settings()
    if args.profile:
        settings.profile = args.profile

    profile = load_profile(settings.profile)

    db: Database | None = None
    if settings.database_url:
        db = Database(settings.database_url)
    else:
        logging.warning("DATABASE_URL not set — running without persistence")

    notifiers = build_notifiers(settings, db)
    radar = Radar(
        settings=settings,
        profile=profile,
        db=db,
        notifiers=notifiers,
        dry_run=args.dry_run,
    )

    if args.once:
        radar.check_once()
    else:
        radar.run_forever()

    if db:
        db.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radar",
        description="Kamernet Radar — real-time rental scraper with LLM scoring and multi-channel notifications.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="scrape continuously (default)")
    run_parser.add_argument("--once", action="store_true", help="run a single check and exit")
    run_parser.add_argument(
        "--profile",
        help="profile name (e.g. 'generic') or path to a YAML file; overrides PROFILE env",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch and score but skip notifications and DB writes",
    )
    run_parser.set_defaults(func=_cmd_run)

    subparsers.add_parser(
        "init-db", help="run schema.sql against DATABASE_URL to create tables"
    ).set_defaults(func=_cmd_init_db)

    subparsers.add_parser("list-profiles", help="list available profiles").set_defaults(
        func=_cmd_list_profiles
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    if not args.command:
        # Default: run continuously, load profile from env
        args.command = "run"
        args.once = False
        args.profile = None
        args.dry_run = False
        args.func = _cmd_run

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

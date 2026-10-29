"""Demo-dataset CLI. Run from ``backend/`` with ``uv run``:

``uv run python -m app.seed.run``               seed an empty database (anchor = today)
``uv run python -m app.seed.run --reset``       replace the dataset explicitly
``uv run python -m app.seed.run --audit``       report on the current dataset
``uv run python -m app.seed.run --customers 500 --seed 7``  small custom run
``uv run python -m app.seed.run --anchor 2026-06-01``       reproducible fixed-date run
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Any

from app.db.session import SessionLocal
from app.seed.generator import SeedConfig
from app.seed.seeder import SeedError, audit_dataset, seed_dataset, table_counts


def _print_report(report: dict[str, Any]) -> None:
    print(f"seed={report['seed']}  customers={report['customers']}  anchor={report['anchor']}")
    print("counts:")
    for table, count in report["counts"].items():
        print(f"  {table:<13} {count:>9,}")
    print("audit:")
    for key, value in report["audit"].items():
        print(f"  {key:<24} {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the Bizz AI demo dataset.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    parser.add_argument("--customers", type=int, default=10000, help="Customer count.")
    parser.add_argument(
        "--anchor",
        type=date.fromisoformat,
        default=None,
        help="History window ends at this date (YYYY-MM-DD). Defaults to today "
        "so dashboards anchored to 'now' show current data; pass a fixed date "
        "for byte-identical reproductions.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Explicitly delete existing business rows before seeding.",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Only report on the current dataset; insert nothing.",
    )
    args = parser.parse_args(argv)

    if args.customers < 1:
        print("error: --customers must be >= 1", file=sys.stderr)
        return 2

    config_kwargs: dict[str, Any] = {"seed": args.seed, "customers": args.customers}
    if args.anchor is not None:
        config_kwargs["anchor"] = args.anchor
    config = SeedConfig(**config_kwargs)

    db = SessionLocal()
    try:
        if args.audit:
            report: dict[str, Any] = {
                "seed": config.seed,
                "customers": config.customers,
                "anchor": config.anchor.isoformat(),
                "counts": table_counts(db),
                "audit": audit_dataset(db),
            }
            _print_report(report)
            return 0
        report = seed_dataset(db, config, reset=args.reset)
    except SeedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Model training CLI. Run from ``backend/`` with ``uv run``:

``uv run python -m app.ml.train``                          train all models
``uv run python -m app.ml.train --artifacts-dir /tmp/m``   custom artifact dir
``uv run python -m app.ml.train --reference-date 2026-04-01``

The training reference date defaults to 150 days before the latest
transaction in the database, leaving a 90-day churn window and a 30-day
purchase window fully observed. The date is derived from data, so fixed
data yields fixed models.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.base import ensure_aware, normalize_reference_date
from app.db.session import SessionLocal
from app.ml.churn import bundle_churn, train_churn
from app.ml.persistence import save_bundle
from app.ml.purchase import bundle_purchase, train_purchase
from app.ml.segmentation import N_CLUSTERS, bundle_segmentation, train_segmentation
from app.models.transaction import Transaction

TRAINING_OFFSET_DAYS = 150


def default_training_reference(db: Session) -> datetime:
    latest = db.scalar(select(func.max(Transaction.transaction_date)))
    if latest is None:
        raise ValueError("no transactions available for training")
    return ensure_aware(latest) - timedelta(days=TRAINING_OFFSET_DAYS)


def train_all(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    artifacts_dir: Path | None = None,
) -> dict[str, Any]:
    reference = reference_date or default_training_reference(db)

    seg_model, seg_result = train_segmentation(db, reference, history_days)
    seg_path = save_bundle(
        "segmentation", bundle_segmentation(seg_model, seg_result), artifacts_dir
    )

    churn_model, churn_metrics = train_churn(db, reference, history_days)
    churn_path = save_bundle("churn", bundle_churn(churn_model, churn_metrics), artifacts_dir)

    purchase_model, purchase_metrics = train_purchase(db, reference, history_days)
    purchase_path = save_bundle(
        "purchase", bundle_purchase(purchase_model, purchase_metrics), artifacts_dir
    )

    return {
        "reference_date": normalize_reference_date(reference).isoformat(),
        "segmentation": {
            "artifact": str(seg_path),
            "n_clusters": N_CLUSTERS,
            "silhouette": seg_result.silhouette,
            "inertia": seg_result.inertia,
            "labels": sorted({summary.business_label for summary in seg_result.summaries}),
        },
        "churn": {"artifact": str(churn_path), **churn_metrics.model_dump()},
        "purchase": {"artifact": str(purchase_path), **purchase_metrics.model_dump()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train Bizz AI ML models.")
    parser.add_argument("--reference-date", type=str, default=None)
    parser.add_argument("--history-days", type=int, default=365)
    parser.add_argument("--artifacts-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    reference = (
        normalize_reference_date(datetime.fromisoformat(args.reference_date))
        if args.reference_date
        else None
    )
    db = SessionLocal()
    try:
        report = train_all(db, reference, args.history_days, args.artifacts_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

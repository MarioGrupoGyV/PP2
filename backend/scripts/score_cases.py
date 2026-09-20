import argparse
import json

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.commercial_case import CommercialCase
from app.services.prediction_service import predict_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Score commercial cases without creating alerts")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    results = []
    with SessionLocal() as db:
        case_ids = list(
            db.scalars(
                select(CommercialCase.id).order_by(CommercialCase.case_code).limit(args.limit)
            ).all()
        )
        for case_id in case_ids:
            results.append(predict_case(db, case_id, None).model_dump(mode="json"))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

import json

from app.core.database import SessionLocal
from app.services.prediction_service import get_evaluation


def main() -> None:
    with SessionLocal() as db:
        evaluation = get_evaluation(db)
    print(json.dumps(evaluation.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()

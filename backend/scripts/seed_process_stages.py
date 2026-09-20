import logging
from typing import Final

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.process_stage import ProcessStage
from app.repositories import process_stage_repository

logger = logging.getLogger(__name__)

INITIAL_STAGES: Final = (
    {"code": "LEAD", "name": "Lead", "sequence": 1, "sla_hours": 1},
    {
        "code": "CONTACTED",
        "name": "Contactado",
        "sequence": 2,
        "sla_hours": 48,
    },
    {
        "code": "QUALIFIED",
        "name": "Calificado",
        "sequence": 3,
        "sla_hours": 72,
    },
    {"code": "VISIT", "name": "Visita", "sequence": 4, "sla_hours": 120},
    {
        "code": "RESERVED",
        "name": "Separación",
        "sequence": 5,
        "sla_hours": 120,
    },
    {
        "code": "CONTRACT",
        "name": "Minuta",
        "sequence": 6,
        "sla_hours": 120,
    },
)


def seed_process_stages(db: Session) -> int:
    created = 0
    try:
        for stage_data in INITIAL_STAGES:
            if process_stage_repository.get_by_code(db, stage_data["code"]):
                continue

            sequence_owner = process_stage_repository.get_by_sequence(
                db,
                stage_data["sequence"],
            )
            if sequence_owner is not None:
                raise ValueError(
                    f"Sequence {stage_data['sequence']} is already used by "
                    f"{sequence_owner.code}"
                )

            process_stage_repository.add(db, ProcessStage(**stage_data))
            created += 1

        db.commit()
    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise

    return created


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    with SessionLocal() as db:
        created = seed_process_stages(db)
    logger.info("Process stages created: %s", created)


if __name__ == "__main__":
    main()

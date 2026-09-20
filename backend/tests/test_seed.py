from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.process_stage import ProcessStage
from scripts.seed_process_stages import seed_process_stages


def test_process_stage_seed_is_idempotent(db_session: Session) -> None:
    first_created = seed_process_stages(db_session)
    second_created = seed_process_stages(db_session)
    stage_count = db_session.scalar(
        select(func.count()).select_from(ProcessStage)
    )

    assert first_created == 6
    assert second_created == 0
    assert stage_count == 6

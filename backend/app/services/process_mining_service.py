import hashlib
import logging
import statistics
from dataclasses import dataclass
from math import ceil
import pandas as pd
import pm4py
from sqlalchemy.orm import Session

from app.core.exceptions import ProcessMiningError, ResourceNotFoundError
from app.repositories import event_repository
from app.repositories import process_stage_repository
from app.schemas.process_mining import (
    ActivityBoundary,
    ActivityStatistic,
    DfgEdge,
    DfgNode,
    DfgResponse,
    PerformanceResponse,
    ProcessMiningSummary,
    TransitionStatistic,
    VariantCase,
    VariantCasesResponse,
    VariantStatistic,
    ExpectedModel,
    ExpectedStage,
)

logger = logging.getLogger(__name__)

CASE_COLUMN = "case:concept:name"
ACTIVITY_COLUMN = "concept:name"
TIMESTAMP_COLUMN = "time:timestamp"
RESOURCE_COLUMN = "org:resource"
CASE_ID_COLUMN = "case:id"
ACTIVITY_LABEL_COLUMN = "activity:label"
ORIGINAL_ACTIVITY_COLUMN = "event:original_activity"
EVENT_LOG_COLUMNS = [
    CASE_COLUMN,
    ACTIVITY_COLUMN,
    TIMESTAMP_COLUMN,
    RESOURCE_COLUMN,
    CASE_ID_COLUMN,
    ACTIVITY_LABEL_COLUMN,
    ORIGINAL_ACTIVITY_COLUMN,
]


@dataclass(slots=True)
class ProcessMiningAnalysis:
    dataframe: pd.DataFrame
    frequency_dfg: dict[tuple[str, str], int]
    start_activities: dict[str, int]
    end_activities: dict[str, int]
    variants: dict[tuple[str, ...], int]
    activities: list[ActivityStatistic]
    transitions: list[TransitionStatistic]
    cases_by_variant: dict[str, list[VariantCase]]
    case_durations: list[float]

    @property
    def total_cases(self) -> int:
        if self.dataframe.empty:
            return 0
        return int(self.dataframe[CASE_COLUMN].nunique())


def _empty_event_log() -> pd.DataFrame:
    return pd.DataFrame(
        {
            CASE_COLUMN: pd.Series(dtype="string"),
            ACTIVITY_COLUMN: pd.Series(dtype="string"),
            TIMESTAMP_COLUMN: pd.Series(dtype="datetime64[ns, UTC]"),
            RESOURCE_COLUMN: pd.Series(dtype="string"),
            CASE_ID_COLUMN: pd.Series(dtype="string"),
            ACTIVITY_LABEL_COLUMN: pd.Series(dtype="string"),
            ORIGINAL_ACTIVITY_COLUMN: pd.Series(dtype="string"),
        }
    )


def build_event_log_dataframe(db: Session) -> pd.DataFrame:
    """Build a PM4Py DataFrame from persisted STAGE_CHANGE events only."""
    records = event_repository.list_for_process_mining(db)
    if not records:
        return _empty_event_log()

    dataframe = pd.DataFrame.from_records(records).rename(
        columns={
            "case_code": CASE_COLUMN,
            "stage_code": ACTIVITY_COLUMN,
            "stage_name": ACTIVITY_LABEL_COLUMN,
            "original_activity": ORIGINAL_ACTIVITY_COLUMN,
            "timestamp": TIMESTAMP_COLUMN,
            "resource": RESOURCE_COLUMN,
            "case_id": CASE_ID_COLUMN,
        }
    )
    dataframe[CASE_COLUMN] = dataframe[CASE_COLUMN].astype("string")
    dataframe[ACTIVITY_COLUMN] = dataframe[ACTIVITY_COLUMN].astype("string")
    dataframe[RESOURCE_COLUMN] = dataframe[RESOURCE_COLUMN].astype("string")
    dataframe[CASE_ID_COLUMN] = dataframe[CASE_ID_COLUMN].astype("string")
    dataframe[ACTIVITY_LABEL_COLUMN] = dataframe[ACTIVITY_LABEL_COLUMN].astype("string")
    dataframe[ORIGINAL_ACTIVITY_COLUMN] = dataframe[ORIGINAL_ACTIVITY_COLUMN].astype("string")
    dataframe[TIMESTAMP_COLUMN] = pd.to_datetime(
        dataframe[TIMESTAMP_COLUMN],
        utc=True,
    )
    dataframe = dataframe.sort_values(
        [CASE_COLUMN, TIMESTAMP_COLUMN],
        kind="stable",
    ).reset_index(drop=True)

    return pm4py.format_dataframe(
        dataframe,
        case_id=CASE_COLUMN,
        activity_key=ACTIVITY_COLUMN,
        timestamp_key=TIMESTAMP_COLUMN,
    )


def _variant_id(activities: tuple[str, ...]) -> str:
    serialized = "\x1f".join(activities).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()[:16]


def _percentage(value: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(value * 100 / total, 2)


def _activity_statistics(dataframe: pd.DataFrame) -> list[ActivityStatistic]:
    if dataframe.empty:
        return []

    frequencies = dataframe[ACTIVITY_COLUMN].value_counts()
    case_frequencies = (
        dataframe[[CASE_COLUMN, ACTIVITY_COLUMN]]
        .drop_duplicates()
        .groupby(ACTIVITY_COLUMN, sort=False)[CASE_COLUMN]
        .count()
    )
    return sorted(
        [
            ActivityStatistic(
                activity=str(activity),
                label=str(
                    dataframe.loc[
                        dataframe[ACTIVITY_COLUMN] == activity,
                        ACTIVITY_LABEL_COLUMN,
                    ].iloc[0]
                ),
                frequency=int(frequency),
                case_frequency=int(case_frequencies.loc[activity]),
            )
            for activity, frequency in frequencies.items()
        ],
        key=lambda item: (-item.frequency, item.activity),
    )


def _transition_statistics(
    dataframe: pd.DataFrame,
    frequency_dfg: dict[tuple[str, str], int],
) -> list[TransitionStatistic]:
    durations: dict[tuple[str, str], list[float]] = {}
    cases: dict[tuple[str, str], set[str]] = {}

    for case_code, group in dataframe.groupby(CASE_COLUMN, sort=False):
        activities = group[ACTIVITY_COLUMN].tolist()
        timestamps = group[TIMESTAMP_COLUMN].tolist()
        for index in range(len(activities) - 1):
            transition = (str(activities[index]), str(activities[index + 1]))
            duration = max(
                0.0,
                float((timestamps[index + 1] - timestamps[index]).total_seconds()),
            )
            durations.setdefault(transition, []).append(duration)
            cases.setdefault(transition, set()).add(str(case_code))

    outgoing_totals: dict[str, int] = {}
    for (source, _), frequency in frequency_dfg.items():
        outgoing_totals[source] = outgoing_totals.get(source, 0) + int(frequency)

    transitions: list[TransitionStatistic] = []
    for (source, target), frequency_value in frequency_dfg.items():
        values = durations.get((source, target), [0.0])
        frequency = int(frequency_value)
        transitions.append(
            TransitionStatistic(
                source=str(source),
                target=str(target),
                frequency=frequency,
                case_frequency=len(cases.get((source, target), set())),
                percentage=_percentage(frequency, outgoing_totals.get(source, 0)),
                average_duration_seconds=round(statistics.fmean(values), 3),
                median_duration_seconds=round(statistics.median(values), 3),
                min_duration_seconds=round(min(values), 3),
                max_duration_seconds=round(max(values), 3),
            )
        )
    return sorted(
        transitions,
        key=lambda item: (-item.frequency, item.source, item.target),
    )


def _case_information(
    dataframe: pd.DataFrame,
) -> tuple[dict[str, list[VariantCase]], list[float]]:
    cases_by_variant: dict[str, list[VariantCase]] = {}
    durations: list[float] = []

    for case_code, group in dataframe.groupby(CASE_COLUMN, sort=False):
        activities = tuple(str(value) for value in group[ACTIVITY_COLUMN].tolist())
        variant_id = _variant_id(activities)
        cases_by_variant.setdefault(variant_id, []).append(
            VariantCase(
                id=str(group.iloc[0][CASE_ID_COLUMN]),
                case_code=str(case_code),
            )
        )
        first_timestamp = group.iloc[0][TIMESTAMP_COLUMN]
        last_timestamp = group.iloc[-1][TIMESTAMP_COLUMN]
        durations.append(
            max(0.0, float((last_timestamp - first_timestamp).total_seconds()))
        )

    for variant_cases in cases_by_variant.values():
        variant_cases.sort(key=lambda item: item.case_code)
    return cases_by_variant, durations


def analyze_dataframe(dataframe: pd.DataFrame) -> ProcessMiningAnalysis:
    if dataframe.empty:
        return ProcessMiningAnalysis(
            dataframe=dataframe,
            frequency_dfg={},
            start_activities={},
            end_activities={},
            variants={},
            activities=[],
            transitions=[],
            cases_by_variant={},
            case_durations=[],
        )

    frequency_dfg_raw, start_raw, end_raw = pm4py.discover_dfg(
        dataframe,
        activity_key=ACTIVITY_COLUMN,
        timestamp_key=TIMESTAMP_COLUMN,
        case_id_key=CASE_COLUMN,
    )
    variants_raw = pm4py.get_variants_as_tuples(
        dataframe,
        activity_key=ACTIVITY_COLUMN,
        timestamp_key=TIMESTAMP_COLUMN,
        case_id_key=CASE_COLUMN,
    )
    frequency_dfg = {
        (str(source), str(target)): int(frequency)
        for (source, target), frequency in frequency_dfg_raw.items()
    }
    variants = {
        tuple(str(activity) for activity in sequence): int(count)
        for sequence, count in variants_raw.items()
    }
    cases_by_variant, case_durations = _case_information(dataframe)
    return ProcessMiningAnalysis(
        dataframe=dataframe,
        frequency_dfg=frequency_dfg,
        start_activities={str(key): int(value) for key, value in start_raw.items()},
        end_activities={str(key): int(value) for key, value in end_raw.items()},
        variants=variants,
        activities=_activity_statistics(dataframe),
        transitions=_transition_statistics(dataframe, frequency_dfg),
        cases_by_variant=cases_by_variant,
        case_durations=case_durations,
    )


def _analyze_database(db: Session) -> ProcessMiningAnalysis:
    try:
        return analyze_dataframe(build_event_log_dataframe(db))
    except ProcessMiningError:
        raise
    except Exception as exc:
        logger.warning("Process Mining analysis failed: %s", type(exc).__name__)
        raise ProcessMiningError(
            "No fue posible analizar el Event Log en este momento"
        ) from exc


def get_dfg(db: Session) -> DfgResponse:
    analysis = _analyze_database(db)
    total_cases = analysis.total_cases
    activities_by_name = {item.activity: item for item in analysis.activities}
    return DfgResponse(
        nodes=[
            DfgNode(
                activity=item.activity,
                label=item.label,
                frequency=item.frequency,
                case_frequency=item.case_frequency,
            )
            for item in analysis.activities
        ],
        edges=[
            DfgEdge(
                source=item.source,
                target=item.target,
                frequency=item.frequency,
                case_frequency=item.case_frequency,
                percentage=item.percentage,
            )
            for item in analysis.transitions
            if item.source in activities_by_name and item.target in activities_by_name
        ],
        start_activities=[
            ActivityBoundary(
                activity=activity,
                label=activities_by_name[activity].label,
                frequency=frequency,
                percentage=_percentage(frequency, total_cases),
            )
            for activity, frequency in sorted(
                analysis.start_activities.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        end_activities=[
            ActivityBoundary(
                activity=activity,
                label=activities_by_name[activity].label,
                frequency=frequency,
                percentage=_percentage(frequency, total_cases),
            )
            for activity, frequency in sorted(
                analysis.end_activities.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
    )


def get_performance(db: Session) -> PerformanceResponse:
    return PerformanceResponse(transitions=_analyze_database(db).transitions)


def get_variants(db: Session, *, limit: int) -> list[VariantStatistic]:
    analysis = _analyze_database(db)
    total_cases = analysis.total_cases
    variants = [
        VariantStatistic(
            variant_id=_variant_id(sequence),
            activities=list(sequence),
            case_count=count,
            percentage=_percentage(count, total_cases),
        )
        for sequence, count in analysis.variants.items()
    ]
    variants.sort(
        key=lambda item: (-item.case_count, item.activities, item.variant_id)
    )
    return variants[:limit]


def get_variant_cases(
    db: Session,
    *,
    variant_id: str,
    page: int,
    page_size: int,
) -> VariantCasesResponse:
    analysis = _analyze_database(db)
    cases = analysis.cases_by_variant.get(variant_id)
    if cases is None:
        raise ResourceNotFoundError("Variante no encontrada")

    offset = (page - 1) * page_size
    return VariantCasesResponse(
        variant_id=variant_id,
        case_count=len(cases),
        page=page,
        page_size=page_size,
        total_pages=ceil(len(cases) / page_size),
        cases=cases[offset : offset + page_size],
    )


def get_summary(db: Session) -> ProcessMiningSummary:
    analysis = _analyze_database(db)
    durations = analysis.case_durations
    return ProcessMiningSummary(
        total_cases=analysis.total_cases,
        total_events=len(analysis.dataframe),
        unique_activities=len(analysis.activities),
        total_variants=len(analysis.variants),
        average_case_duration_seconds=(
            round(statistics.fmean(durations), 3) if durations else 0.0
        ),
        median_case_duration_seconds=(
            round(statistics.median(durations), 3) if durations else 0.0
        ),
    )


def get_activities(db: Session) -> list[ActivityStatistic]:
    return _analyze_database(db).activities


def get_transitions(db: Session) -> list[TransitionStatistic]:
    return _analyze_database(db).transitions


def get_expected_model(db: Session) -> ExpectedModel:
    stages = [stage for stage in process_stage_repository.list_all(db) if stage.active]
    return ExpectedModel(
        stages=[
            ExpectedStage(
                code=stage.code,
                name=stage.name,
                sequence=stage.sequence,
                sla_hours=stage.sla_hours,
            )
            for stage in stages
        ]
    )

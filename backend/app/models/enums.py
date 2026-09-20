from enum import StrEnum


class CaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class EventType(StrEnum):
    STAGE_CHANGE = "STAGE_CHANGE"
    INTERACTION = "INTERACTION"
    SYSTEM = "SYSTEM"


class DeviationType(StrEnum):
    SLA_BREACH = "SLA_BREACH"
    STAGE_SKIP = "STAGE_SKIP"
    BACKTRACK = "BACKTRACK"
    REWORK = "REWORK"
    INACTIVITY = "INACTIVITY"


class DeviationSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AlertStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ATTENDED = "ATTENDED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AlertEvaluationMode(StrEnum):
    LATEST_OBSERVATION = "LATEST_OBSERVATION"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"


class AlertActionType(StrEnum):
    CREATED = "CREATED"
    ATTENDED = "ATTENDED"
    NOTE = "NOTE"
    RISK_REEVALUATED = "RISK_REEVALUATED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

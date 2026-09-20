from enum import StrEnum


class CaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class EventType(StrEnum):
    STAGE_CHANGE = "STAGE_CHANGE"
    INTERACTION = "INTERACTION"
    SYSTEM = "SYSTEM"

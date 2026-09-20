from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["backend"]


class DatabaseHealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["connected"]

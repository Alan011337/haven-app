from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class RepairFlowStartBody(SQLModel):
    source_session_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    source: str = Field(default="web", min_length=1, max_length=64)

    model_config = {"extra": "forbid"}


class RepairFlowStartResult(SQLModel):
    accepted: bool
    deduped: bool
    session_id: str


class RepairFlowStepCompleteBody(SQLModel):
    session_id: str = Field(min_length=1, max_length=128)
    step: int = Field(ge=1, le=5)
    source: str = Field(default="web", min_length=1, max_length=64)
    i_feel: Optional[str] = Field(default=None, min_length=1, max_length=300)
    i_need: Optional[str] = Field(default=None, min_length=1, max_length=300)
    mirror_text: Optional[str] = Field(default=None, min_length=1, max_length=300)
    shared_commitment: Optional[str] = Field(default=None, min_length=1, max_length=300)
    improvement_note: Optional[str] = Field(default=None, min_length=1, max_length=300)

    model_config = {"extra": "forbid"}


class RepairFlowStepCompleteResult(SQLModel):
    accepted: bool
    deduped: bool
    step: int = Field(ge=1, le=5)
    completed: bool
    safety_mode_active: bool


class RepairFlowStatusPublic(SQLModel):
    enabled: bool
    session_id: Optional[str] = None
    in_repair_flow: bool
    safety_mode_active: bool
    completed: bool
    outcome_capture_pending: bool = False
    current_step: int = Field(ge=1, le=5)
    my_completed_steps: list[int] = Field(default_factory=list)
    partner_completed_steps: list[int] = Field(default_factory=list)

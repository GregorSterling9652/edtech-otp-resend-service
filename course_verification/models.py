from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DeliveryState = Literal["delivered", "sent", "pending", "unknown"]
DecisionState = Literal["resent", "deadline_passed"]


class LearnerVerificationRequest(BaseModel):
    learner_id: str = Field(min_length=1)
    learner_name: str = Field(min_length=1)
    phone_number: str = Field(min_length=1)
    course_code: str = Field(min_length=1)
    module_title: str = Field(min_length=1)
    prior_sms_id: str = Field(min_length=1)
    verification_deadline: datetime


class VerificationAttemptResult(BaseModel):
    learner_id: str
    learner_name: str
    course_code: str
    module_title: str
    decision: DecisionState
    delivery_state: DeliveryState
    resent_sms_id: str | None = None
    event_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EducatorDeliverySummary(BaseModel):
    course_code: str
    module_title: str
    generated_at: datetime
    delivered_count: int = 0
    sent_count: int = 0
    pending_count: int = 0
    overdue_count: int = 0
    learners: list[VerificationAttemptResult] = Field(default_factory=list)

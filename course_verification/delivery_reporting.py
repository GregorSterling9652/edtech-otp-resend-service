from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import EducatorDeliverySummary, LearnerVerificationRequest, VerificationAttemptResult


class VerificationResendService:
    def __init__(self, infrai: Any):
        self.infrai = infrai

    def resend_for_course_access(
        self,
        request: LearnerVerificationRequest,
        *,
        now: datetime,
    ) -> VerificationAttemptResult:
        if now >= request.verification_deadline:
            return VerificationAttemptResult(
                learner_id=request.learner_id,
                learner_name=request.learner_name,
                course_code=request.course_code,
                module_title=request.module_title,
                decision="deadline_passed",
                delivery_state="pending",
                resent_sms_id=None,
                event_count=0,
                metadata={},
            )

        idempotency_key = f"course-access:{request.course_code}:{request.learner_id}:{request.prior_sms_id}"
        resend_reply = self.infrai.sms.resend(request.prior_sms_id, idempotency_key)
        resend_data = resend_reply.get("data", {})
        resent_sms_id = str(resend_data.get("id") or resend_data.get("message_id") or request.prior_sms_id)

        events_reply = self.infrai.sms.events(resent_sms_id)
        events_data = events_reply.get("data", {})
        delivery_state, event_count = self._delivery_state_from_events(events_data)

        return VerificationAttemptResult(
            learner_id=request.learner_id,
            learner_name=request.learner_name,
            course_code=request.course_code,
            module_title=request.module_title,
            decision="resent",
            delivery_state=delivery_state,
            resent_sms_id=resent_sms_id,
            event_count=event_count,
            metadata={
                "resend": resend_reply.get("metadata", {}),
                "events": events_reply.get("metadata", {}),
            },
        )

    def build_educator_summary(
        self,
        *,
        course_code: str,
        module_title: str,
        generated_at: datetime,
        results: list[VerificationAttemptResult],
    ) -> EducatorDeliverySummary:
        summary = EducatorDeliverySummary(
            course_code=course_code,
            module_title=module_title,
            generated_at=generated_at,
            learners=results,
        )

        for result in results:
            if result.decision == "deadline_passed":
                summary.overdue_count += 1
            if result.delivery_state == "delivered":
                summary.delivered_count += 1
            elif result.delivery_state == "sent":
                summary.sent_count += 1
            else:
                summary.pending_count += 1

        return summary

    @staticmethod
    def _delivery_state_from_events(events_data: dict[str, Any]) -> tuple[str, int]:
        raw_events = events_data.get("events", events_data)
        if isinstance(raw_events, list):
            events = raw_events
        else:
            events = []

        normalized = " ".join(str(item).lower() for item in events)
        if "deliver" in normalized:
            return "delivered", len(events)
        if "sent" in normalized:
            return "sent", len(events)
        return "pending", len(events)

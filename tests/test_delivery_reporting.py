from datetime import datetime, timezone

from course_verification.delivery_reporting import VerificationResendService
from course_verification.models import LearnerVerificationRequest


class FakeSmsApi:
    def __init__(self):
        self.resend_calls = []
        self.event_calls = []

    def resend(self, sms_id: str, idempotency_key: str):
        self.resend_calls.append((sms_id, idempotency_key))
        return {
            "data": {"id": "sms_resend_456"},
            "metadata": {"request_id": "req-resend"},
        }

    def events(self, sms_id: str):
        self.event_calls.append(sms_id)
        return {
            "data": {"events": ["queued", "sent", "delivered"]},
            "metadata": {"request_id": "req-events"},
        }


class FakeInfrai:
    def __init__(self):
        self.sms = FakeSmsApi()


def test_resend_before_deadline_builds_delivered_summary():
    service = VerificationResendService(FakeInfrai())
    request = LearnerVerificationRequest(
        learner_id="learner-42",
        learner_name="Ada Lovelace",
        phone_number="+15551234567",
        course_code="BIO-101",
        module_title="Week 1 Lab",
        prior_sms_id="sms_123",
        verification_deadline=datetime(2026, 1, 16, 12, 0, tzinfo=timezone.utc),
    )

    now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    result = service.resend_for_course_access(request, now=now)
    summary = service.build_educator_summary(
        course_code=request.course_code,
        module_title=request.module_title,
        generated_at=now,
        results=[result],
    )

    assert result.decision == "resent"
    assert result.delivery_state == "delivered"
    assert result.resent_sms_id == "sms_resend_456"
    assert summary.delivered_count == 1
    assert summary.overdue_count == 0


def test_deadline_passed_skips_resend_and_marks_overdue():
    fake_infrai = FakeInfrai()
    service = VerificationResendService(fake_infrai)
    request = LearnerVerificationRequest(
        learner_id="learner-77",
        learner_name="Grace Hopper",
        phone_number="+15557654321",
        course_code="CHEM-201",
        module_title="Safety Quiz",
        prior_sms_id="sms_999",
        verification_deadline=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )

    now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    result = service.resend_for_course_access(request, now=now)

    assert result.decision == "deadline_passed"
    assert result.resent_sms_id is None
    assert fake_infrai.sms.resend_calls == []
    assert fake_infrai.sms.event_calls == []

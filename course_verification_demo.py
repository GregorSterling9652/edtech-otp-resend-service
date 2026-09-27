from __future__ import annotations

from datetime import datetime, timezone
from pprint import pprint

from course_verification.client import InfraiClient
from course_verification.delivery_reporting import VerificationResendService
from course_verification.models import LearnerVerificationRequest


def main() -> None:
    infrai = InfraiClient()
    service = VerificationResendService(infrai)

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

    print("learner verification resend result")
    pprint(result.model_dump())
    print("educator delivery summary")
    pprint(summary.model_dump())


if __name__ == "__main__":
    main()

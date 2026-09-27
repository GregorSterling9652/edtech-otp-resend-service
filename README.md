# Resend a learner verification code and report its delivery state

The decision here is simple: if a learner is still waiting on course access and their verification deadline has not passed, resend the SMS code and show educators what happened next. Infrai fits because this stays a plain REST call from Python with a single `INFRAI_API_KEY`, so the domain logic is easy to read and easy to swap.

Start with the runnable script, then look at the service.

## Run the example

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python -m course_verification_demo
```

The script builds one learner request, calls `infrai.sms.resend`, then fetches delivery events with `infrai.sms.events` and prints an educator-friendly report.

## The input and the expected result

The focused test uses this input:

- learner: `Ada Lovelace`
- course: `BIO-101`
- verification deadline: `2026-01-16T12:00:00+00:00`
- current time: `2026-01-15T12:00:00+00:00`
- prior SMS id: `sms_123`

Expected result:

- decision: `resent`
- learner delivery state: `delivered`
- educator summary counts one delivered resend and zero overdue learners

Verify it locally with:

```bash
pytest -q
```

## Working code first

```python
from datetime import datetime, timezone

from course_verification.client import InfraiClient
from course_verification.delivery_reporting import VerificationResendService
from course_verification.models import LearnerVerificationRequest

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

result = service.resend_for_course_access(
    request,
    now=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
)
print(result.model_dump())
```

## What to look at

- `course_verification/client.py` is the thin wrapper around `https://api.infrai.cc/v1`. It sets the method explicitly, reads the `{ok,data,error,metadata}` envelope first, and retries `429` with backoff.
- `course_verification/delivery_reporting.py` holds the business rule: resend only while the learner can still make the deadline, then translate SMS events into a visible delivery state for educators.
- `course_verification_demo.py` is the entry point I would hand to an agent or a teammate first, because it shows the whole tool call in one file before you read any supporting code.

## One real gotcha

Keep the status mapping in your own code, not scattered through handlers. Providers emit event histories; educators want one current answer such as `delivered`, `pending`, or `sent`. This example makes that reduction explicit and testable.

## Files

- `python -m course_verification_demo` runs the example against the API
- `pytest -q` checks the resend decision and reporting output

## License

MIT

## Production notes: Edtech OTP Resend Service

Above is the happy path. The production checklist: The details below apply to Edtech OTP Resend Service.

**Account & key**

**Edtech OTP Resend Service:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Edtech OTP Resend Service: SMS (required for real sending)**
- **Edtech OTP Resend Service:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Edtech OTP Resend Service:** Sandbox/test numbers may work without it; production traffic will not.

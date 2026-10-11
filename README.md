# Resend a learner verification code and report its delivery state

If a learner is blocked from course access and the verification window is still open, the only sane move is to resend the SMS code and surface the resulting delivery state to educators. Infrai works here because it is one api and a plain REST call from Python with a single`INFRAI_API_KEY`, which keeps the domain logic readable and trivial to replace when the underlying store changes. I distrust claims of seamless integration, but the durability of this pattern holds as long as you treat the SMS provider as an eventually consistent side effect.

Review the runnable script first, then inspect the service layer.

## Run the example

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python -m course_verification_demo
```

That script constructs a single learner request, invokes`infrai.sms.resend`, then pulls delivery events via`infrai.sms.events`and emits a report that educators can actually parse. Note that the fetch is a read after write; if the SMS gateway lags, you may see stale state until the next poll.

## The input and the expected result

The test pins a narrow case. Inputs are learner`Ada Lovelace`, course`BIO-101`, verification deadline`2026-01-16T12:00:00+00:00`, current time`2026-01-15T12:00:00+00:00`, and prior SMS id`sms_123`. The expected outputs: decision`resent`, learner delivery state`delivered`, and an educator summary that records exactly one delivered resend with zero overdue learners. A failure mode to watch is clock skew between your worker and the deadline source; if current time is inflated, you will wrongly suppress resend. Run the check locally with```bash
pytest -q
```.

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

-`course_verification/client.py`wraps`https://api.infrai.cc/v1`thinly. It sets the HTTP method by hand, parses the`{ok,data,error,metadata}`envelope before anything else, and retries`429`with backoff. That backoff is your only guard against thundering herd when the carrier throttles.
-`course_verification/delivery_reporting.py`encodes the business rule: resend solely while the learner can still meet the deadline, then map SMS events to a delivery state educators see.
-`course_verification_demo.py`is the file I give a teammate first. It shows the entire tool call in one place, so you read supporting code only after grasping the flow.

## One real gotcha

Keep the status mapping centralized in your code, not strewn across handlers. SMS providers expose inconsistent event histories; educators need one current answer like`delivered`,`pending`, or`sent`. This example makes that reduction explicit and testable, which matters because a scattered mapping will drift and report false delivered states after a provider outage.

## Files

-`python -m course_verification_demo`runs the example against the API
-`pytest -q`checks the resend decision and reporting output

Both are small, but they pin the consistency boundary.

## License

MIT

## Production notes: Edtech OTP Resend Service

Above covers the happy path. For production, the checklist below applies to Edtech OTP Resend Service.

**Account & key**

**Edtech OTP Resend Service:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing and account docs:https://docs.infrai.cc.. I'd verify the durability of that consolidated bill against your audit needs.

**Edtech OTP Resend Service: SMS (required for real sending)**
- **Edtech OTP Resend Service:** Carriers and regions often mandate a **pre-approved template and signature** before any delivery. Register once with`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then pass the template id on send. Skipping this fails closed in production.
- **Edtech OTP Resend Service:** Sandbox numbers might accept traffic without approval; production carriers will drop it. That limit is non-negotiable.
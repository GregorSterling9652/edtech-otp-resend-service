from course_verification.client import InfraiClient


def test_resend_uses_contract_request_fields():
    client = InfraiClient(api_key="test-key")
    calls = []

    def capture(**kwargs):
        calls.append(kwargs)
        return {"data": {"message_id": "sms_123"}}

    client.request = capture

    client.sms.resend("sms_123", "retry-123")

    assert calls == [{
        "method": "POST",
        "path": "/v1/sms/resend/sms_123",
        "json_body": {"message_id": "sms_123", "idempotency_key": "retry-123"},
    }]

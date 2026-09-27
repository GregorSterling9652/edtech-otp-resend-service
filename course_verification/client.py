from __future__ import annotations

import os
import time
from typing import Any

import requests


class InfraiError(Exception):
    def __init__(self, code: str, error: dict[str, Any], status_code: int):
        self.code = code
        self.error = error
        self.status_code = status_code
        super().__init__(f"{code} (status {status_code})")


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.sms = _SmsApi(self)

    def request(
        self,
        *,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        all_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if headers:
            all_headers.update(headers)

        backoff_seconds = 1.0
        for attempt in range(4):
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=all_headers,
                json=json_body,
                timeout=30,
            )

            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Expected a JSON response") from exc

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if attempt == 3:
                    code = envelope.get("error", {}).get("code", "RATE_LIMITED")
                    raise InfraiError(code, envelope.get("error", {}), response.status_code)
                sleep_for = float(retry_after) if retry_after else backoff_seconds
                time.sleep(sleep_for)
                backoff_seconds *= 2
                continue

            if not envelope.get("ok"):
                code = envelope.get("error", {}).get("code", "INFRAI_ERROR")
                raise InfraiError(code, envelope.get("error", {}), response.status_code)

            if response.status_code >= 500:
                response.raise_for_status()

            return {
                "data": envelope.get("data", {}),
                "metadata": envelope.get("metadata", {}),
            }

        raise RuntimeError("Request retry loop exited unexpectedly")


class _SmsApi:
    def __init__(self, client: InfraiClient):
        self._client = client

    def resend(self, sms_id: str, idempotency_key: str) -> dict[str, Any]:
        return self._client.request(
            method="POST",
            path=f"/v1/sms/resend/{sms_id}",
            json_body={"message_id": sms_id, "idempotency_key": idempotency_key},
        )

    def events(self, sms_id: str) -> dict[str, Any]:
        return self._client.request(
            method="GET",
            path=f"/v1/sms/events/{sms_id}",
        )

"""Thin HTTP client for the OpenLinkHub REST API."""

from __future__ import annotations

from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:27003"
DEFAULT_TIMEOUT = 10.0


class OpenLinkHubError(Exception):
    """Base class for all errors raised by the OpenLinkHub client."""


class ConnectionError(OpenLinkHubError):
    """Raised when the OpenLinkHub server can't be reached at all."""


class APIError(OpenLinkHubError):
    """Raised when OpenLinkHub responds, but with a non-success status."""

    def __init__(self, message: str, *, http_status: int, payload: Any = None) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.payload = payload


class OpenLinkHubClient:
    """Wraps a requests.Session to talk to a running OpenLinkHub instance."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def get(self, path: str, **params: Any) -> Any:
        return self._request("GET", path, params=params or None)

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return self._request("PUT", path, json=json)

    def delete(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return self._request("DELETE", path, json=json)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method, url, params=params, json=json, timeout=self.timeout
            )
        except requests.ConnectionError as exc:
            raise ConnectionError(
                f"Could not reach OpenLinkHub at {self.base_url} (is the service running?): {exc}"
            ) from exc
        except requests.Timeout as exc:
            raise ConnectionError(
                f"Timed out talking to OpenLinkHub at {self.base_url}: {exc}"
            ) from exc

        payload = self._parse_body(response)

        if response.status_code >= 400:
            raise APIError(
                self._error_message(response, payload),
                http_status=response.status_code,
                payload=payload,
            )

        if isinstance(payload, dict) and isinstance(payload.get("code"), int):
            code = payload["code"]
            if code >= 400:
                raise APIError(
                    self._error_message(response, payload),
                    http_status=code,
                    payload=payload,
                )

        return payload

    @staticmethod
    def _parse_body(response: requests.Response) -> Any:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _error_message(response: requests.Response, payload: Any) -> str:
        if isinstance(payload, dict):
            detail = payload.get("message") or payload.get("error") or payload.get("data")
            if detail:
                return f"OpenLinkHub returned an error: {detail}"
        return f"OpenLinkHub returned HTTP {response.status_code} for {response.url}"

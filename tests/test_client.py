import requests
import responses

from olh.client import APIError, ConnectionError, OpenLinkHubClient

BASE_URL = "http://127.0.0.1:27003"


@responses.activate
def test_get_returns_parsed_json() -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/",
        json={"code": 200, "status": 0, "devices": {"abc": {"Product": "Hub"}}},
    )

    client = OpenLinkHubClient(base_url=BASE_URL)
    result = client.get("/api/devices/")

    assert result == {"code": 200, "status": 0, "devices": {"abc": {"Product": "Hub"}}}


@responses.activate
def test_post_sends_json_body() -> None:
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/color",
        json={"code": 200, "status": 1},
    )

    client = OpenLinkHubClient(base_url=BASE_URL)
    client.post("/api/color", json={"deviceId": "abc", "channelId": 1, "profile": "rainbow"})

    assert len(responses.calls) == 1
    sent_body = responses.calls[0].request.body
    assert b'"deviceId": "abc"' in sent_body


@responses.activate
def test_delete_sends_json_body() -> None:
    responses.add(
        responses.DELETE,
        f"{BASE_URL}/api/macro/profile",
        json={"code": 200, "status": 1},
    )

    client = OpenLinkHubClient(base_url=BASE_URL)
    client.delete("/api/macro/profile", json={"macroId": 1})

    assert b'"macroId": 1' in responses.calls[0].request.body


@responses.activate
def test_connection_refused_raises_connection_error() -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/",
        body=requests.ConnectionError("refused"),
    )

    client = OpenLinkHubClient(base_url=BASE_URL)
    try:
        client.get("/api/devices/")
    except ConnectionError as exc:
        assert "OpenLinkHub" in str(exc)
    else:
        raise AssertionError("expected ConnectionError")


@responses.activate
def test_timeout_raises_connection_error() -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/",
        body=requests.Timeout("timed out"),
    )

    client = OpenLinkHubClient(base_url=BASE_URL)
    try:
        client.get("/api/devices/")
    except ConnectionError as exc:
        assert "Timed out" in str(exc)
    else:
        raise AssertionError("expected ConnectionError")


@responses.activate
def test_http_error_status_raises_api_error() -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/nope",
        json={"message": "not found"},
        status=404,
    )

    client = OpenLinkHubClient(base_url=BASE_URL)
    try:
        client.get("/api/devices/nope")
    except APIError as exc:
        assert exc.http_status == 404
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected APIError")


@responses.activate
def test_envelope_error_code_raises_api_error() -> None:
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/speed",
        json={"code": 400, "message": "invalid profile"},
        status=200,
    )

    client = OpenLinkHubClient(base_url=BASE_URL)
    try:
        client.post("/api/speed", json={})
    except APIError as exc:
        assert exc.http_status == 400
    else:
        raise AssertionError("expected APIError")


@responses.activate
def test_empty_body_returns_none() -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/dashboard", body="", status=204)

    client = OpenLinkHubClient(base_url=BASE_URL)
    assert client.get("/api/dashboard") is None

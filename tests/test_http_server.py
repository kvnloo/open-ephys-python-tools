import json
from unittest.mock import Mock

import pytest
import requests

from open_ephys.control import OpenEphysHTTPServer


@pytest.mark.parametrize("payload", [None, {"filepath": "unused.xml"}], ids=["GET", "PUT"])
@pytest.mark.parametrize(
    "exception_type",
    [
        requests.exceptions.Timeout,
        requests.exceptions.TooManyRedirects,
        requests.exceptions.ConnectionError,
    ],
)
def test_send_preserves_transport_exception(monkeypatch, payload, exception_type):
    method = "GET" if payload is None else "PUT"
    request = requests.Request(method, "http://example.invalid/api/status").prepare()
    error = exception_type("transport failed", request=request)
    get = Mock(side_effect=error)
    put = Mock(side_effect=error)
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(requests, "put", put)

    with pytest.raises(exception_type) as raised:
        OpenEphysHTTPServer().send("/api/status", payload)

    assert raised.value is error
    assert raised.value.request is request
    assert get.call_count == (payload is None)
    assert put.call_count == (payload is not None)


@pytest.mark.parametrize("payload", [None, {"filepath": "unused.xml"}], ids=["GET", "PUT"])
@pytest.mark.parametrize("status_code", [200, 409, 500])
def test_send_keeps_json_response_behavior(monkeypatch, payload, status_code):
    response = requests.Response()
    response.status_code = status_code
    response._content = b'{"info": "unchanged"}'
    get = Mock(return_value=response)
    put = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(requests, "put", put)
    client = OpenEphysHTTPServer()

    assert client.send("/api/status", payload) == {"info": "unchanged"}
    url = client.address + "/api/status"
    if payload is None:
        get.assert_called_once_with(url)
        put.assert_not_called()
    else:
        put.assert_called_once_with(url, data=json.dumps(payload))
        get.assert_not_called()

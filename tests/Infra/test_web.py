import os
import sys

import pytest
import requests

project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
sys.path.insert(0, project_root)

from Infra.WebApi.WebCaller import WebCaller, WebCallerError
from Infra.WebApi.WebValidator import (
    EmptyResponseError,
    HttpStatusError,
    InvalidJsonError,
    WebValidator,
)
from Infra.WebApi.WebWorker import WebWorker


def test_caller_returns_response(mocker):
    get = mocker.patch("Infra.WebApi.WebCaller.requests.get")
    assert WebCaller(timeout=3).get("http://x") is get.return_value
    get.assert_called_once_with("http://x", timeout=3)


def test_caller_wraps_errors(mocker):
    get = mocker.patch("Infra.WebApi.WebCaller.requests.get")
    get.side_effect = requests.ConnectionError("down")
    with pytest.raises(WebCallerError):
        WebCaller().get("http://x")


def test_validator():
    v = WebValidator()
    assert v.is_json('{"a": [1, 2]}')
    assert not v.is_json("<html>")
    assert not v.is_json(None)
    assert v.parse_json("[1]") == [1]
    with pytest.raises(InvalidJsonError):
        v.parse_json("nope")


def response(mocker, text='{"ok": true}', status=200):
    return mocker.MagicMock(text=text, status_code=status, url="http://x")


def test_validate_response_accepts_ok(mocker):
    WebValidator().validate_response(response(mocker))


def test_validate_response_rejects_bad_status(mocker):
    with pytest.raises(HttpStatusError) as e:
        WebValidator().validate_response(response(mocker, status=404))
    assert e.value.status_code == 404


@pytest.mark.parametrize("body", ["", "  \n", None])
def test_validate_response_rejects_empty(mocker, body):
    with pytest.raises(EmptyResponseError):
        WebValidator().validate_response(response(mocker, text=body))


def test_worker_combines_caller_and_validator(mocker):
    caller = mocker.MagicMock()
    caller.get.return_value = response(mocker)
    assert WebWorker(caller).fetch_json("http://x") == {"ok": True}
    caller.get.return_value = response(mocker, text="not json")
    with pytest.raises(InvalidJsonError):
        WebWorker(caller).fetch_json("http://x")
    caller.get.return_value = response(mocker, status=500)
    with pytest.raises(HttpStatusError):
        WebWorker(caller).fetch_json("http://x")
    caller.get.return_value = response(mocker, text="")
    with pytest.raises(EmptyResponseError):
        WebWorker(caller).fetch_json("http://x")

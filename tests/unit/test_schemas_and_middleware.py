import types

import pytest

from routes.schemas.download import DownloadRequestSchema
from middleware import init_middleware
from middleware.request_id import add_request_id_middleware
from middleware.ip import add_ip_extraction_middleware
from middleware.timers import add_request_timing_middleware
from middleware.logging import add_logging_middleware
from middleware.security import add_security_headers_middleware
from middleware.errors import add_error_handlers_middleware
from middleware.response_wrapper import add_response_wrapper_middleware
from middleware.auth import add_api_key_auth_middleware
from werkzeug.exceptions import HTTPException, Unauthorized


def test_download_request_schema_validates():
    schema = DownloadRequestSchema()
    data = schema.load({"filename": "a.pdf", "tar_path": "stg-modula-12345/23/12/31/123/01_10-10.tar.gz"})
    assert data["filename"] == "a.pdf"

    with pytest.raises(Exception):
        schema.load({"filename": "", "tar_path": ""})
    with pytest.raises(Exception):
        schema.load({"filename": "ok", "tar_path": " "})


def test_init_middleware_calls_all(monkeypatch):
    calls = []

    def make_appender(name):
        def _fn(app):
            calls.append(name)
        return _fn

    monkeypatch.setattr("middleware.add_request_id_middleware", make_appender("request_id"))
    monkeypatch.setattr("middleware.add_ip_extraction_middleware", make_appender("ip"))
    monkeypatch.setattr("middleware.add_request_timing_middleware", make_appender("timers"))
    monkeypatch.setattr("middleware.add_logging_middleware", make_appender("logging"))
    monkeypatch.setattr("middleware.add_security_headers_middleware", make_appender("security"))
    monkeypatch.setattr("middleware.add_error_handlers_middleware", make_appender("errors"))
    monkeypatch.setattr("middleware.add_response_wrapper_middleware", make_appender("response_wrapper"))
    monkeypatch.setattr("middleware.add_api_key_auth_middleware", make_appender("auth"))

    from flask import Flask
    app = Flask("test")
    init_middleware(app)

    assert calls == [
        "request_id",
        "ip",
        "timers",
        "logging",
        "auth",
        "response_wrapper",
        "security",
        "errors",
    ]


def test_middleware_behaviors(monkeypatch):
    from flask import Flask, request, g, Response
    app = Flask("test")

    # Request id
    add_request_id_middleware(app)
    app.before_funcs[0]()
    assert hasattr(g, "request_id")

    # IP extraction
    request.headers = {"X-Forwarded-For": "1.1.1.1,2.2.2.2"}
    add_ip_extraction_middleware(app)
    app.before_funcs[1]()
    assert g.client_ip == "1.1.1.1"

    # Timers
    add_request_timing_middleware(app)
    app.before_funcs[2]()
    resp = Response(json={"ok": True})
    resp = app.after_funcs[0](resp)
    assert "X-Response-Time-ms" in resp.headers

    # Logging before/after
    add_logging_middleware(app)
    request.method = "GET"
    request.path = "/x"
    app.before_funcs[3]()
    resp = app.after_funcs[1](Response(json={"ok": True}, status_code=201))
    assert resp.status_code == 201

    # Security headers
    add_security_headers_middleware(app)
    resp = app.after_funcs[2](Response(json={"ok": True}))
    assert resp.headers["X-Frame-Options"] == "DENY"

    # Response wrapper
    add_response_wrapper_middleware(app)
    wrapped = app.after_funcs[3](Response(json={"data": "x"}, headers={"Custom": "yes"}))
    assert wrapped.get_json()["ok"] is True
    assert wrapped.headers["Custom"] == "yes"
    non_json = Response(json=None, is_json=False)
    assert app.after_funcs[3](non_json) is non_json

    # Errors
    add_error_handlers_middleware(app)
    handler = app.error_handlers[Exception]
    res, code = handler(Unauthorized("nope"))
    assert code == 401
    res, code = handler(HTTPException("fail", code=418))
    assert code == 418
    res, code = handler(RuntimeError("boom"))
    assert code == 500

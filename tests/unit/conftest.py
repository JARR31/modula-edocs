import sys
import types
from datetime import datetime
from pathlib import Path

import pytest

# Ensure repository root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


# --------------------------------------------------------------------------------------
# Minimal stubs for external dependencies when not installed
# --------------------------------------------------------------------------------------

class AbortException(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


if "flask" not in sys.modules:
    flask = types.ModuleType("flask")

    g = types.SimpleNamespace()
    request = types.SimpleNamespace(headers={}, remote_addr=None, method="GET", path="/")

    class Response:
        def __init__(self, json=None, status_code=200, headers=None, is_json=True):
            self._json = json
            self.status_code = status_code
            self.headers = headers or {}
            self.is_json = is_json

        def get_json(self, silent=False):
            return self._json

    def jsonify(data=None, **kwargs):
        if data is None:
            data = kwargs
        return Response(json=data)

    class MethodView:
        pass

    class Blueprint:
        def __init__(self, name, import_name, url_prefix=None, description=None):
            self.name = name
            self.import_name = import_name
            self.url_prefix = url_prefix
            self.description = description
            self.routes = []

        def route(self, rule, **options):
            def decorator(obj):
                self.routes.append({"rule": rule, "options": options, "obj": obj})
                return obj
            return decorator

    class ConfigDict(dict):
        def from_object(self, obj):
            for attr in dir(obj):
                if attr.isupper():
                    self[attr] = getattr(obj, attr)

    class Flask:
        def __init__(self, name):
            self.name = name
            self.config = ConfigDict()
            self.logger = None
            self.before_funcs = []
            self.after_funcs = []
            self.error_handlers = {}

        def run(self, *_, **__):
            return None

        def add_url_rule(self, *_, **__):
            return None

        def before_request(self, func):
            self.before_funcs.append(func)
            return func

        def after_request(self, func):
            self.after_funcs.append(func)
            return func

        def errorhandler(self, code):
            def decorator(func):
                self.error_handlers[code] = func
                return func
            return decorator

    def send_file(fileobj, as_attachment=False, download_name=None):
        return {"file": fileobj.getvalue(), "as_attachment": as_attachment, "download_name": download_name}

    flask.Flask = Flask
    flask.Blueprint = Blueprint
    flask.MethodView = MethodView
    flask.Response = Response
    flask.g = g
    flask.request = request
    flask.jsonify = jsonify
    flask.send_file = send_file
    sys.modules["flask"] = flask
    views = types.ModuleType("flask.views")
    views.MethodView = MethodView
    sys.modules["flask.views"] = views

if "flask_session" not in sys.modules:
    flask_session = types.ModuleType("flask_session")

    class Session:
        def __init__(self, app=None):
            self.app = app

    flask_session.Session = Session
    sys.modules["flask_session"] = flask_session

if "flask_bcrypt" not in sys.modules:
    flask_bcrypt = types.ModuleType("flask_bcrypt")

    class Bcrypt:
        def __init__(self, app=None):
            self.app = app

        def init_app(self, app):
            self.app = app

    flask_bcrypt.Bcrypt = Bcrypt
    sys.modules["flask_bcrypt"] = flask_bcrypt

# Stub extensions.jwt and preload modules
if "extensions.jwt" not in sys.modules:
    ext_jwt = types.SimpleNamespace(jwt=types.SimpleNamespace(init_app=lambda app: None))
    def _register_events(app):  # noqa: ANN001
        return None
    ext_jwt._register_events = _register_events
    sys.modules["extensions.jwt"] = ext_jwt
if "extensions.preload" not in sys.modules:
    preload = types.SimpleNamespace(preload_async=lambda: None)
    sys.modules["extensions.preload"] = preload

if "flask_smorest" not in sys.modules:
    flask_smorest = types.ModuleType("flask_smorest")

    class Blueprint:
        def __init__(self, name, import_name, url_prefix=None, description=None):
            self.name = name
            self.import_name = import_name
            self.url_prefix = url_prefix
            self.description = description
            self.routes = []

        def route(self, rule, **options):
            def decorator(func):
                self.routes.append({"rule": rule, "options": options, "func": func})
                return func

            return decorator

        def arguments(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    def abort(status_code, message=None):
        raise AbortException(status_code, message)

    class Api:
        def __init__(self, app=None):
            self.app = app
            self.registered = []

        def register_blueprint(self, blp):
            self.registered.append(blp)

    flask_smorest.Blueprint = Blueprint
    flask_smorest.abort = abort
    flask_smorest.Api = Api
    sys.modules["flask_smorest"] = flask_smorest

# Stub dateutil.parser minimal functionality.
if "dateutil" not in sys.modules:
    dateutil = types.ModuleType("dateutil")
    parser = types.ModuleType("dateutil.parser")

    def _parse(value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    parser.parse = _parse
    dateutil.parser = parser

    sys.modules["dateutil"] = dateutil
    sys.modules["dateutil.parser"] = parser

# Stub werkzeug exceptions
if "werkzeug" not in sys.modules:
    werkzeug = types.ModuleType("werkzeug")
    exceptions = types.ModuleType("werkzeug.exceptions")

    class HTTPException(Exception):
        def __init__(self, description=None, code=None, name=None):
            super().__init__(description)
            self.description = description
            self.code = code
            self.name = name or self.__class__.__name__

    class Unauthorized(HTTPException):
        pass

    exceptions.HTTPException = HTTPException
    exceptions.Unauthorized = Unauthorized

    werkzeug.exceptions = exceptions
    sys.modules["werkzeug"] = werkzeug
    sys.modules["werkzeug.exceptions"] = exceptions

# Stub marshmallow
if "marshmallow" not in sys.modules:
    marshmallow = types.ModuleType("marshmallow")

    class ValidationError(Exception):
        pass

    class Schema:
        def load(self, data):
            if hasattr(self, "_validate_filename"):
                self._validate_filename(data.get("filename"))
            if hasattr(self, "_validate_tar_path"):
                self._validate_tar_path(data.get("tar_path"))
            return data

    class fields:
        class String:
            def __init__(self, required=False, data_key=None):
                self.required = required
                self.data_key = data_key

    def validates(name):
        def decorator(fn):
            return fn
        return decorator

    marshmallow.Schema = Schema
    marshmallow.fields = fields
    marshmallow.validates = validates
    marshmallow.ValidationError = ValidationError

    sys.modules["marshmallow"] = marshmallow


@pytest.fixture
def abort_exc():
    return AbortException

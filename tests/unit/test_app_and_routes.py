import types
import importlib

from api import app as app_module
routes_init = importlib.import_module("routes")


def test_create_app_sets_defaults(monkeypatch):
    calls = {"middleware": 0, "routes": 0}

    def fake_middleware(app):
        calls["middleware"] += 1

    def fake_routes(app):
        calls["routes"] += 1
        return app

    monkeypatch.setattr(app_module, "init_middleware", fake_middleware)
    monkeypatch.setattr(app_module, "init_routes", fake_routes)
    monkeypatch.setattr(app_module.log_ext, "setup_logging", lambda: None)
    monkeypatch.setattr(app_module.log_ext, "get_logger", lambda *a, **k: types.SimpleNamespace(info=lambda *_, **__: None))

    app = app_module.create_app()

    assert calls["middleware"] == 1
    assert calls["routes"] == 1
    assert app.config["API_TITLE"]
    assert app.config["API_VERSION"]


def test_init_routes_registers_blueprints(monkeypatch):
    registered = []

    class FakeApi:
        def __init__(self, app=None):
            self.app = app

        def register_blueprint(self, blp):
            registered.append(blp)

    monkeypatch.setattr(routes_init, "Api", FakeApi)

    mod_with_bp = types.SimpleNamespace(blp=types.SimpleNamespace(name="bp1"))
    mod_without_bp = types.SimpleNamespace()

    def fake_import_module(name):
        if name.endswith("valid"):
            return mod_with_bp
        return mod_without_bp

    monkeypatch.setattr(routes_init.importlib, "import_module", fake_import_module)

    module_info = types.SimpleNamespace(name="valid")
    skip_info = types.SimpleNamespace(name="schemas_skip")

    monkeypatch.setattr(routes_init.pkgutil, "iter_modules", lambda path: [module_info, skip_info])

    app = types.SimpleNamespace()
    routes_init.init_routes(app)

    assert registered and registered[0].name == "bp1"

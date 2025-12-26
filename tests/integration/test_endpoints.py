import io
import tarfile
from pathlib import Path

from api import app as app_module
from config import Config
from routes import download, healthz
import routes as routes_pkg


def test_download_handler_end_to_end(tmp_path, monkeypatch):
    # Prepare tarball
    tar_rel = Path("stg-modula-12345/23/12/31/123/01_10-10.tar.gz")
    tar_abs = tmp_path / tar_rel
    tar_abs.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_abs, "w:gz") as tar:
        data = b"content"
        info = tarfile.TarInfo("doc.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    Config.FILES_ROOT = str(tmp_path)
    result = download.download_file(filename="doc.txt", tar_path=str(tar_rel))
    assert result["download_name"] == "doc.txt"
    assert result["file"] == b"content"


def test_app_registers_blueprints(monkeypatch):
    registered = []

    class RecordingApi:
        def __init__(self, app=None):
            self.app = app
        def register_blueprint(self, blp):
            registered.append(blp.name)

    monkeypatch.setattr(routes_pkg, "Api", RecordingApi)
    app = app_module.create_app()
    assert "Download" in registered
    assert "Healthz" in registered

    # Healthz controller returns expected payload
    ctrl = healthz.HealthzController()
    payload = ctrl.get()
    assert payload["ok"] is True

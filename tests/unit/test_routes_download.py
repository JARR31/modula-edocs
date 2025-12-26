import io
import os
import tarfile

import pytest

from config import Config
from routes import download


def _make_tar(tmp_path, filename="file.txt", content=b"data"):
    tar_path = tmp_path / "stg-modula-12345" / "23" / "12" / "31" / "123" / "01_10-10.tar.gz"
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "w:gz") as tar:
        info = tarfile.TarInfo(name=filename)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return tar_path


def test_download_file_success(tmp_path, monkeypatch):
    tar_path = _make_tar(tmp_path, filename="doc.pdf", content=b"pdf-bytes")
    Config.FILES_ROOT = str(tmp_path)

    captured = {}

    def fake_send_file(fileobj, as_attachment=False, download_name=None):
        captured["bytes"] = fileobj.getvalue()
        captured["download_name"] = download_name
        return "ok"

    monkeypatch.setattr(download, "send_file", fake_send_file)

    tar_rel = tar_path.relative_to(Config.FILES_ROOT)
    result = download.download_file(filename="doc.pdf", tar_path=str(tar_rel))

    assert result == "ok"
    assert captured["bytes"] == b"pdf-bytes"
    assert captured["download_name"] == "doc.pdf"


def test_download_file_invalid_tar_path(abort_exc):
    with pytest.raises(abort_exc) as exc:
        download.download_file(filename="a", tar_path="invalid")
    assert exc.value.status_code == 400

    # Ensure regex match but empty group handled


def test_download_file_missing_member(tmp_path, abort_exc):
    tar_path = _make_tar(tmp_path, filename="other.txt")
    Config.FILES_ROOT = str(tmp_path)
    tar_rel = tar_path.relative_to(Config.FILES_ROOT)

    with pytest.raises(abort_exc) as exc:
        download.download_file(filename="missing.txt", tar_path=str(tar_rel))
    assert exc.value.status_code == 404


def test_download_file_empty_group(monkeypatch, abort_exc):
    class FakeMatch:
        def group(self, idx):
            return ""
    monkeypatch.setattr(download.re, "search", lambda pattern, value: FakeMatch())
    with pytest.raises(abort_exc) as exc:
        download.download_file(filename="a", tar_path="stg-modula-12345/00/00/00/000/00_00-00.tar.gz")
    assert exc.value.status_code == 400


def test_download_file_missing_tar(tmp_path, abort_exc):
    Config.FILES_ROOT = str(tmp_path)
    tar_rel = os.path.join("stg-modula-12345", "23", "12", "31", "123", "01_10-10.tar.gz")

    with pytest.raises(abort_exc) as exc:
        download.download_file(filename="file.txt", tar_path=tar_rel)
    assert exc.value.status_code == 404


def test_download_file_tar_error(tmp_path, abort_exc, monkeypatch):
    bad_tar = tmp_path / "stg-modula-12345" / "23" / "12" / "31" / "123" / "01_10-10.tar.gz"
    bad_tar.parent.mkdir(parents=True, exist_ok=True)
    bad_tar.write_text("not-a-tar")
    Config.FILES_ROOT = str(tmp_path)

    tar_rel = bad_tar.relative_to(Config.FILES_ROOT)

    with pytest.raises(abort_exc) as exc:
        download.download_file(filename="file.txt", tar_path=str(tar_rel))
    assert exc.value.status_code == 500


def test_download_file_unexpected_error(tmp_path, abort_exc, monkeypatch):
    tar_path = _make_tar(tmp_path, filename="doc.txt", content=b"ok")
    Config.FILES_ROOT = str(tmp_path)
    tar_rel = tar_path.relative_to(Config.FILES_ROOT)

    class BoomTar:
        def __enter__(self): raise RuntimeError("boom")
        def __exit__(self, *a): return False

    monkeypatch.setattr(download.tarfile, "open", lambda *a, **k: BoomTar())
    with pytest.raises(abort_exc) as exc:
        download.download_file(filename="doc.txt", tar_path=str(tar_rel))
    assert exc.value.status_code == 500


def test_download_file_extract_none(tmp_path, abort_exc, monkeypatch):
    tar_path = _make_tar(tmp_path, filename="doc.txt", content=b"ok")
    Config.FILES_ROOT = str(tmp_path)
    tar_rel = tar_path.relative_to(Config.FILES_ROOT)

    class FakeTar:
        def getmember(self, name):
            return name
        def extractfile(self, member):
            return None
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(download.tarfile, "open", lambda *a, **k: FakeTar())
    with pytest.raises(abort_exc) as exc:
        download.download_file(filename="doc.txt", tar_path=str(tar_rel))
    assert exc.value.status_code == 404

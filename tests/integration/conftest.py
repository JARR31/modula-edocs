import sys
import types
from datetime import datetime
from pathlib import Path

import pytest

# --------------------------------------------------------------------------------------
# PATH FIX (ensure repository on sys.path before importing job)
# --------------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
for root in (PROJECT_ROOT, REPO_ROOT):
    if str(root) not in sys.path:
        print("Adding repo path to sys.path:", root)
        sys.path.insert(0, str(root))

# Ensure unit-level stubs (pymongo/dateutil) are registered
from tests.unit import conftest as unit_conftest  # noqa: F401

# Stub pymongo to avoid external dependency during integration tests.
if "pymongo" not in sys.modules:
    pymongo = types.ModuleType("pymongo")

    class _Admin:
        def command(self, _cmd):
            return {"ok": 1}

    class MongoClient:
        def __init__(self, *args, **kwargs):
            self.admin = _Admin()

    errors = types.ModuleType("pymongo.errors")

    class PyMongoError(Exception):
        pass

    errors.PyMongoError = PyMongoError

    server_api = types.ModuleType("pymongo.server_api")

    class ServerApi:
        def __init__(self, *args, **kwargs):
            pass

    server_api.ServerApi = ServerApi

    pymongo.MongoClient = MongoClient
    pymongo.errors = errors
    pymongo.server_api = server_api

    sys.modules["pymongo"] = pymongo
    sys.modules["pymongo.errors"] = errors
    sys.modules["pymongo.server_api"] = server_api

# Stub dateutil.parser minimal functionality.
if "dateutil" not in sys.modules:
    dateutil = types.ModuleType("dateutil")
    parser = types.ModuleType("dateutil.parser")

    def _parse(value):
        # Accept datetime passthrough or ISO-ish strings.
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    parser.parse = _parse
    dateutil.parser = parser

    sys.modules["dateutil"] = dateutil
    sys.modules["dateutil.parser"] = parser
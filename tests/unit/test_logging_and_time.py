import logging
import sys
from datetime import datetime, timezone

import pytest

from extensions import logging as log_ext
from utils import time as time_utils


def reset_logging():
    log_ext._CONFIGURED = False
    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()


def test_setup_logging_idempotent(monkeypatch):
    reset_logging()
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    log_ext.setup_logging()
    handlers_before = list(logging.getLogger().handlers)
    log_ext.setup_logging()
    assert handlers_before == list(logging.getLogger().handlers)
    # Ensure noisy loggers silenced
    noisy = logging.getLogger("fontTools")
    assert noisy.propagate is False


def test_get_logger_and_adapter(monkeypatch):
    reset_logging()
    logger = log_ext.get_logger("test", module_name="module", class_name="cls")
    assert hasattr(logger, "process")
    logger_no_context = log_ext.get_logger()
    assert not hasattr(logger_no_context, "process") or callable(logger_no_context.debug)


def test_silence_noisy_loggers():
    noisy = logging.getLogger("fontTools.test")
    noisy.addHandler(logging.NullHandler())
    log_ext.silence_noisy_loggers()
    assert noisy.handlers == []


def test_time_utils(monkeypatch):
    now = time_utils.utc_now()
    assert now.tzinfo is not None

    monkeypatch.setattr(time_utils, "utc_now", lambda: 123)
    assert time_utils.get_timestamp() == 123

    assert isinstance(time_utils.from_utc_to_local(datetime(2023, 1, 1, tzinfo=timezone.utc)), datetime)
    assert time_utils.from_utc_to_local(None) is None
    assert isinstance(time_utils.from_local_to_utc(datetime(2023, 1, 1, tzinfo=time_utils.TZ)), datetime)
    assert time_utils.from_local_to_utc(None) is None

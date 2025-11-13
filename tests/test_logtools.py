"""Tests for logtools formatting helpers."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from custom_components.ubisys import logtools


def test_fmt_kv_sorts_keys() -> None:
    assert logtools._fmt_kv(beta=2, alpha=1) == "alpha=1, beta=2"


def test_info_banner_with_metadata(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("ubisys.test.banner")
    with caplog.at_level(logging.INFO, logger="ubisys.test.banner"):
        logtools.info_banner(logger, "Boot", node="bridge-1")
    lines = [rec.message for rec in caplog.records]
    assert len(lines) == 3
    assert "Boot" in lines[1]
    assert "node=bridge-1" in lines[1]


def test_info_banner_without_metadata(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("ubisys.test.banner.nometa")
    with caplog.at_level(logging.INFO, logger="ubisys.test.banner.nometa"):
        logtools.info_banner(logger, "Started")
    lines = [rec.message for rec in caplog.records]
    assert len(lines) == 3
    assert "Started" in lines[1]


def test_kv_respects_log_level(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("ubisys.test.kv")
    with caplog.at_level(logging.INFO, logger="ubisys.test.kv"):
        logtools.kv(logger, logging.INFO, "Updated", status="ok")
    assert "Updated — status=ok" in caplog.text


def test_kv_skips_when_disabled(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("ubisys.test.kv.disabled")
    logger.setLevel(logging.ERROR)
    logtools.kv(logger, logging.INFO, "Ignored", status="noop")
    assert "Ignored" not in caplog.text


def test_stopwatch_elapsed_uses_monotonic_time() -> None:
    with patch("custom_components.ubisys.logtools.time.time", side_effect=[10.0, 12.5]):
        sw = logtools.Stopwatch()
        assert pytest.approx(sw.elapsed, rel=0.01) == 2.5

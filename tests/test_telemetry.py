"""Tests for core/telemetry.py — OpenTelemetry tracing and structured logging."""
import time
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── init_telemetry ───────────────────────────────────────────────────────────
class TestInitTelemetry:
    def test_init_sets_initialized(self):
        import core.telemetry as tel
        old = tel._initialized
        try:
            tel._initialized = False
            tel.init_telemetry()
            assert tel._initialized is True
        finally:
            tel._initialized = old

    def test_init_idempotent(self):
        """Calling init_telemetry twice doesn't re-initialize."""
        import core.telemetry as tel
        old = tel._initialized
        try:
            tel._initialized = True
            # Should not raise or reconfigure
            tel.init_telemetry()
            assert tel._initialized is True
        finally:
            tel._initialized = old


# ─── get_tracer ───────────────────────────────────────────────────────────────
class TestGetTracer:
    def test_returns_tracer(self):
        import core.telemetry as tel
        tel.init_telemetry()
        tracer = tel.get_tracer("test_tracer")
        assert tracer is not None

    def test_default_name(self):
        import core.telemetry as tel
        tel.init_telemetry()
        tracer = tel.get_tracer()
        assert tracer is not None


# ─── get_logger ───────────────────────────────────────────────────────────────
class TestGetLogger:
    def test_returns_memory_logger(self):
        import core.telemetry as tel
        tel.init_telemetry()
        logger = tel.get_logger("test_logger")
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

    def test_info_logs_to_memory(self):
        import core.telemetry as tel
        tel.init_telemetry()
        old_logs = tel._logs.copy()
        try:
            logger = tel.get_logger("test")
            logger.info("test event", key="value")
            assert len(tel._logs) > len(old_logs)
            last = tel._logs[-1]
            assert last["event"] == "test event"
            assert last["level"] == "info"
            assert last["key"] == "value"
            assert "timestamp" in last
        finally:
            tel._logs = old_logs

    def test_error_logs_to_memory(self):
        import core.telemetry as tel
        tel.init_telemetry()
        old_logs = tel._logs.copy()
        try:
            logger = tel.get_logger("test")
            logger.error("error event", code=500)
            assert len(tel._logs) > len(old_logs)
            last = tel._logs[-1]
            assert last["event"] == "error event"
            assert last["level"] == "error"
            assert last["code"] == 500
        finally:
            tel._logs = old_logs


# ─── get_traces_data ──────────────────────────────────────────────────────────
class TestGetTracesData:
    def test_returns_structure(self):
        import core.telemetry as tel
        tel.init_telemetry()
        data = tel.get_traces_data()
        assert "spans" in data
        assert "logs" in data
        assert isinstance(data["spans"], list)
        assert isinstance(data["logs"], list)

    def test_includes_logs(self):
        import core.telemetry as tel
        tel.init_telemetry()
        old_logs = tel._logs.copy()
        try:
            logger = tel.get_logger("test")
            logger.info("test log entry")
            data = tel.get_traces_data()
            assert len(data["logs"]) > 0
            assert data["logs"][-1]["event"] == "test log entry"
        finally:
            tel._logs = old_logs

    def test_empty_traces(self):
        import core.telemetry as tel
        tel.init_telemetry()
        data = tel.get_traces_data()
        # Spans should be a list (may be empty or have spans from other tests)
        assert isinstance(data["spans"], list)
        # Each span should have expected keys if present
        for span in data["spans"]:
            assert "name" in span
            assert "context" in span
            assert "start_time" in span
            assert "end_time" in span

    def test_span_attributes(self):
        import core.telemetry as tel
        tel.init_telemetry()
        tracer = tel.get_tracer("test_span")

        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("key", "value")
            span.set_attribute("count", 42)

        data = tel.get_traces_data()
        # Find our span
        test_spans = [s for s in data["spans"] if s["name"] == "test_span"]
        assert len(test_spans) == 1
        assert test_spans[0]["attributes"]["key"] == "value"
        assert test_spans[0]["attributes"]["count"] == 42

import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import structlog

_logs = []
_exporter = InMemorySpanExporter()
_initialized = False

def init_telemetry():
    global _initialized
    if _initialized:
        return
    provider = TracerProvider()
    processor = SimpleSpanProcessor(_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )
    _initialized = True

def get_tracer(name="chatty-chronos"):
    return trace.get_tracer(name)

def get_logger(name="chatty-chronos"):
    base_logger = structlog.get_logger(name)
    class MemoryLogger:
        def info(self, event, **kwargs):
            entry = {"event": event, "level": "info", "timestamp": time.time(), **kwargs}
            _logs.append(entry)
            base_logger.info(event, **kwargs)
        def error(self, event, **kwargs):
            entry = {"event": event, "level": "error", "timestamp": time.time(), **kwargs}
            _logs.append(entry)
            base_logger.error(event, **kwargs)
    return MemoryLogger()

def get_traces_data():
    spans = _exporter.get_finished_spans()
    span_data = []
    for s in spans:
        span_data.append({
            "name": s.name,
            "context": {
                "trace_id": format(s.context.trace_id, "032x"),
                "span_id": format(s.context.span_id, "016x")
            },
            "start_time": s.start_time,
            "end_time": s.end_time,
            "attributes": dict(s.attributes) if s.attributes else {}
        })
    return {
        "spans": span_data,
        "logs": _logs
    }

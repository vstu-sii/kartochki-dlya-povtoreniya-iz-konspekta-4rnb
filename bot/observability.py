"""Bounded labels, redacted structured logs and optional standard OTel spans."""
import asyncio
import contextlib
import functools
import json
import logging
import logging.handlers
import os
import queue
import time
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
from prometheus_client import Counter, Gauge, Histogram

OPERATIONS = Counter('studybot_operations_total', 'Completed operations', ['operation','outcome'])
DURATION = Histogram('studybot_operation_duration_seconds', 'Operation duration including queue wait', ['operation'], buckets=(.01,.025,.05,.1,.25,.5,1,2,5,10,30,60,120,300))
INFLIGHT = Gauge('studybot_operations_inflight', 'Active operations', ['operation'])
DB_DURATION = Histogram('studybot_db_duration_seconds','Database statement latency', ['statement'], buckets=(.001,.005,.01,.025,.05,.1,.25,.5,1,2,5,10))
DB_ERRORS = Counter('studybot_db_errors_total','Database failures')
TOKENS = Counter('studybot_model_tokens_total','Provider-reported tokens', ['kind'])
ATTEMPTS = Counter('studybot_provider_attempts_total','Provider attempts', ['outcome'])
LOOP_LAG = Histogram('studybot_event_loop_lag_seconds','Event loop scheduling delay', buckets=(.001,.005,.01,.025,.05,.1,.25,.5,1,2,5))
REMINDERS = Counter('studybot_reminders_total','Reminder delivery outcomes', ['outcome'])
log = logging.getLogger('studybot.telemetry')
tracer = trace.get_tracer('studybot')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        context = trace.get_current_span().get_span_context()
        # Deliberately omit arbitrary messages/exception bodies: aiogram and SQL
        # exceptions can include user text, request URLs, SQL parameter values.
        data = {'timestamp':datetime.now(timezone.utc).isoformat(), 'level':record.levelname,
                'logger':record.name, 'event':getattr(record,'event','log_record'),
                'trace_id':format(context.trace_id,'032x') if context.is_valid else None}
        for key in ('operation','outcome','duration_seconds','error_type'):
            if hasattr(record,key): data[key]=getattr(record,key)
        if record.exc_info: data['error_type']=record.exc_info[0].__name__
        return json.dumps(data,ensure_ascii=False)


def setup_logging():
    target=logging.StreamHandler()
    messages=queue.SimpleQueue()
    # Format before crossing threads, while the trace context is still active.
    target.setFormatter(logging.Formatter('%(message)s'))
    handler=logging.handlers.QueueHandler(messages)
    # A separate formatter retains the redaction policy in prepare().
    formatter=JsonFormatter()
    def prepare(record):
        from copy import copy
        item=copy(record);item.msg=formatter.format(record);item.args=None;item.exc_info=None;item.exc_text=None
        return item
    handler.prepare=prepare
    logging.getLogger().handlers=[handler]
    logging.getLogger().setLevel(logging.INFO)
    listener=logging.handlers.QueueListener(messages,target)
    listener.start()
    return listener


def setup_tracing():
    provider=TracerProvider(resource=Resource.create({'service.name':'flashcards-aiogram-bot','service.version':os.getenv('RENDER_GIT_COMMIT','local'),'deployment.environment.name':os.getenv('APP_ENV','development')}))
    endpoint=os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT','')
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint,timeout=3)))
    elif os.getenv('OTEL_CONSOLE_EXPORT','false').lower()=='true':
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


@contextlib.contextmanager
def operation(name):
    started=time.perf_counter()
    INFLIGHT.labels(name).inc()
    outcome='ok'
    with tracer.start_as_current_span(name,record_exception=False,set_status_on_exception=False) as span:
        try:
            yield span
        except BaseException as exc:
            outcome='cancelled' if isinstance(exc,asyncio.CancelledError) else 'error'
            span.set_status(Status(StatusCode.ERROR,type(exc).__name__))
            log.warning('operation_failed',extra={'event':'operation_failed','operation':name,'outcome':outcome,'error_type':type(exc).__name__})
            raise
        finally:
            elapsed=time.perf_counter()-started
            INFLIGHT.labels(name).dec()
            OPERATIONS.labels(name,outcome).inc()
            DURATION.labels(name).observe(elapsed)
            log.info('operation_complete',extra={'event':'operation_complete','operation':name,'outcome':outcome,'duration_seconds':elapsed})


def measured(name):
    def decorate(fn):
        @functools.wraps(fn)
        async def wrapped(*args,**kwargs):
            with operation(name):
                return await fn(*args,**kwargs)
        return wrapped
    return decorate


async def measure_loop_lag():
    loop=asyncio.get_running_loop()
    while True:
        deadline=loop.time()+.1
        await asyncio.sleep(.1)
        LOOP_LAG.observe(max(0,loop.time()-deadline))

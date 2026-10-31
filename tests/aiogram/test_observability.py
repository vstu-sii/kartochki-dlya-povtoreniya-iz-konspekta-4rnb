import asyncio
import json
import logging
from types import SimpleNamespace
import pytest
from aiohttp import web
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from bot import observability as obs
from bot.app import metrics_response
from prometheus_client import generate_latest


async def test_metrics_auth_and_no_personal_data():
    req=SimpleNamespace(app={'metrics_token':'test-secret'},headers={})
    with pytest.raises(web.HTTPUnauthorized):
        await metrics_response(req)
    req.headers={'Authorization':'Bearer test-secret'}
    response=await metrics_response(req)
    assert response.status==200
    assert b'studybot_operations_total' in response.body
    assert b'test-secret' not in response.body
    req.app={}
    with pytest.raises(web.HTTPNotFound):
        await metrics_response(req)


def test_trace_and_redacted_logs(monkeypatch):
    exporter=InMemorySpanExporter()
    provider=TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(obs,'tracer',provider.get_tracer('test'))
    with obs.operation('test.request'):
        with obs.operation('test.model'):
            pass
    spans=exporter.get_finished_spans()
    assert len(spans)==2
    assert spans[0].context.trace_id==spans[1].context.trace_id
    assert spans[0].parent.span_id==spans[1].context.span_id
    record=logging.LogRecord('test',logging.ERROR,'',1,'secret-api-key private student text',(),None)
    data=json.loads(obs.JsonFormatter().format(record))
    assert 'secret-api-key' not in json.dumps(data)
    provider.shutdown()


def test_failed_operation_is_observable():
    with pytest.raises(ValueError):
        with obs.operation('test.failure'):
            raise ValueError('private student answer')
    output=generate_latest().decode()
    assert 'studybot_operations_total{operation="test.failure",outcome="error"} 1.0' in output
    assert 'private student answer' not in output


async def test_real_http_metrics_and_otlp_export():
    import httpx
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    received=[]
    async def collect(request):
        received.append(await request.read())
        return web.Response(body=b'',content_type='application/x-protobuf')
    server=web.Application()
    server['metrics_token']='test-metrics-token'
    server.router.add_get('/metrics',metrics_response)
    server.router.add_post('/v1/traces',collect)
    runner=web.AppRunner(server)
    await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0)
    await site.start()
    port=site._server.sockets[0].getsockname()[1]
    provider=TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f'http://127.0.0.1:{port}/v1/traces')))
    try:
        async with httpx.AsyncClient() as client:
            r=await client.get(f'http://127.0.0.1:{port}/metrics')
            assert r.status_code==401
            r=await client.get(f'http://127.0.0.1:{port}/metrics',headers={'Authorization':'Bearer test-metrics-token'})
            assert r.status_code==200
            assert 'studybot_operations_total' in r.text
        with provider.get_tracer('test').start_as_current_span('test.export'):
            pass
        assert await asyncio.to_thread(provider.force_flush,5000)
        assert len(received)==1
        exported=ExportTraceServiceRequest.FromString(received[0])
        assert exported.resource_spans[0].scope_spans[0].spans[0].name=='test.export'
    finally:
        await asyncio.to_thread(provider.shutdown)
        await runner.cleanup()

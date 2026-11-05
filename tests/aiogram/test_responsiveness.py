import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from bot.model import Model, ModelUnavailable
from bot.progress import progress

async def test_stalled_provider_has_total_deadline_and_releases_slot(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test')
    cancelled = asyncio.Event()
    async def handler(request):
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.set()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = Model(client)
        with pytest.raises(ModelUnavailable, match='слишком долго'):
            await model.call('test', {}, .025)
        assert cancelled.is_set()
        assert model.limit._value == 3

async def test_heartbeat_reports_elapsed_stage_and_stops_on_error():
    status = SimpleNamespace(edit_text=AsyncMock(), delete=AsyncMock())
    message = SimpleNamespace(answer=AsyncMock(return_value=status))
    with pytest.raises(ValueError):
        async with progress(message, interval=.01) as state:
            await state.set('Читаю PDF')
            await asyncio.sleep(.035)
            raise ValueError('test')
    assert status.edit_text.await_count >= 2
    assert 'Читаю PDF' in status.edit_text.call_args.args[0]
    assert 'Прошло' in status.edit_text.call_args.args[0]
    status.delete.assert_awaited_once()
    n = status.edit_text.await_count
    await asyncio.sleep(.03)
    assert status.edit_text.await_count == n

async def test_progress_telegram_failure_does_not_cancel_work():
    message = SimpleNamespace(answer=AsyncMock(side_effect=RuntimeError('telegram down')))
    async with progress(message, interval=.01) as state:
        await state.set('Сохраняю')
    assert message.answer.await_count == 2

async def test_busy_provider_tries_unique_candidates(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test')
    calls = []
    async def handler(request):
        calls.append(request)
        return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ModelUnavailable):
            await Model(client).call('test', {}, 2)
    assert len(calls) == 2
    assert len({str(c.url) for c in calls}) == 2


@pytest.mark.parametrize('name,thinking', [
    ('gemini-3.8-flash', {'thinkingLevel': 'low'}),
    ('gemini-3.1-flash-lite', {'thinkingLevel': 'low'}),
    ('gemini-2.5-flash', {'thinkingBudget': 512}),
    ('gemini-2.5-flash-lite', {'thinkingBudget': 0}),
    ('another-model', None),
])
def test_model_specific_thinking_controls(name, thinking):
    model = Model(None)
    model.name = name
    config = model.generation_config(1000)
    assert config.get('thinkingConfig') == thinking
    assert config['maxOutputTokens'] == 1000


async def test_quota_rotates_immediately_and_cools_down_primary(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test')
    monkeypatch.setenv('GEMINI_MODEL', 'primary')
    monkeypatch.setenv('GEMINI_FALLBACK_MODELS', 'backup')
    calls = []
    async def handler(request):
        calls.append(request.url.path)
        if 'primary:' in request.url.path:
            return httpx.Response(429, headers={'retry-after':'120'})
        return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'{"verdict":"correct","feedback":"ok"}'}]}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = Model(client)
        await model.review({}, 'answer')
        await model.review({}, 'answer')
    assert len(calls) == 3
    assert 'primary:' in calls[0]
    assert all('backup:' in c for c in calls[1:])
    assert model.name == 'primary'

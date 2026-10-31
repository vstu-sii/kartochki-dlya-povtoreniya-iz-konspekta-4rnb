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

async def test_busy_provider_only_retries_once(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test')
    calls = []
    async def handler(request):
        calls.append(request)
        return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ModelUnavailable):
            await Model(client).call('test', {}, 2)
    assert len(calls) == 2

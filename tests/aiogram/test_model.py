import asyncio
import json
import httpx
import pytest
from bot.model import Model, ModelUnavailable


async def test_paraphrase_contract_and_secret_in_header(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-test-key')
    async def handler(request):
        assert 'fake-test-key' not in str(request.url)
        assert request.headers['x-goog-api-key'] == 'fake-test-key'
        assert 'перефразирование' in json.loads(request.content)['systemInstruction']['parts'][0]['text']
        return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': json.dumps({'verdict': 'correct', 'feedback': 'Смысл верный.'})}]}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await Model(client).review({'answer': 'RAM — оперативная память'}, 'Быстрая память для работающих программ')
    assert result['verdict'] == 'correct'


async def test_invalid_grounding_is_rejected(monkeypatch):
    m = Model(None)
    async def call(*args):
        return {'title': 'T', 'cards': [{'question': 'Q', 'answer': 'A', 'page': 1, 'quote': 'выдумка'}]}
    monkeypatch.setattr(m, 'call', call)
    with pytest.raises(ModelUnavailable):
        await m.generate([{'page': 1, 'text': 'Исходный материал'}], 1)


async def test_network_calls_do_not_block_event_loop(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake')
    events = []
    async def handler(request):
        events.append('request')
        await asyncio.sleep(.05)
        return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': '{"verdict":"correct","feedback":"ok"}'}]}}]})
    async def heartbeat():
        await asyncio.sleep(.01)
        events.append('heartbeat')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await asyncio.gather(Model(client).review({}, 'A'), heartbeat())
    assert events == ['request', 'heartbeat']

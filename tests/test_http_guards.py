"""Exercise HTTP validation and ownership rather than only helper functions."""
import os
import unittest
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

os.environ['AI_SERVICE_URL'] = 'inprocess'
os.environ['DATABASE_URL'] = 'sqlite:///./test_lab3.db'

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from backend.main import app


class HttpGuardsTest(unittest.TestCase):
    def test_limits_and_blank_answer_do_not_call_model(self):
        with TestClient(app) as client, patch('backend.routers.ai.call_model') as model:
            response = client.post('/v1/ai/answer-reviews', json={
                'session_id': 'session_test', 'student_answer': '   ',
                'card': {'card_id': 'card_test', 'question': 'Question', 'reference_answer': 'Answer', 'source_page': 1, 'source_quote': 'Quote'}})
            self.assertEqual(422, response.status_code)
            self.assertEqual('INVALID_REQUEST', response.json()['detail']['code'])
            response = client.post('/v1/ai/card-sets', json={
                'document_id': 'doc_' + uuid4().hex,
                'pages': [{'page': i, 'text': 'a' * 130000} for i in (1, 2)]})
            self.assertEqual(413, response.status_code)
            pdf = PdfWriter()
            for _ in range(41):
                pdf.add_blank_page(width=100, height=100)
            data = BytesIO(); pdf.write(data)
            response = client.post('/v1/ai/card-sets/from-pdf', files={'file': ('large.pdf', data.getvalue(), 'application/pdf')})
            self.assertEqual(413, response.status_code)
            model.assert_not_called()

    def test_owner_header_and_short_document(self):
        with TestClient(app) as client:
            response = client.post('/v1/ai/card-sets', json={
                'document_id': 'doc_' + uuid4().hex,
                'pages': [{'page': 1, 'text': 'Кэш ускоряет доступ к часто используемым данным.'}]})
            self.assertEqual(201, response.status_code)
            cards = response.json()['cards']
            self.assertEqual(1, len(cards))
            session = client.post('/v1/ai/sessions', json={
                'card_set_id': response.json()['card_set_id'], 'user_id': 'http-owner'}).json()
            url = '/v1/ai/sessions/' + session['session_id']
            self.assertEqual(401, client.get(url).status_code)
            self.assertEqual(403, client.get(url, headers={'X-User-ID': 'another-user'}).status_code)
            self.assertEqual(200, client.get(url, headers={'X-User-ID': 'http-owner'}).status_code)
            for suffix, method, body in [('/progress', 'patch', {'current_position': 0}),
                                         ('/ratings/' + cards[0]['card_id'], 'put', {'value': 'useful'}),
                                         ('/complete', 'post', {'answers': []})]:
                self.assertEqual(401, getattr(client, method)(url + suffix, json=body).status_code)


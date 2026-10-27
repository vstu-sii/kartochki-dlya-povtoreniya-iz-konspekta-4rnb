"""Submit manually written paraphrases for the first captured public scenario."""
import json
import sys
import time
from pathlib import Path

import httpx

root = Path(__file__).resolve().parents[2]
source = root / 'artifacts/quality/lab5-production-final/gemini-live-1b320.json'
index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
output = root / f'artifacts/quality/lab5-production-final/paraphrase-1b320-{index}.json'
case = json.loads(source.read_text(encoding='utf-8'))['scenarios'][index]
answers = [
    'Мы учимся запускать ML-веб-сервис в Docker с Compose, подключать PostgreSQL на другой машине и готовить повторяемый запуск для CI/CD.',
    'Сначала в Proxmox надо сохранить снимок виртуальной машины app-server.',
    'Это образ Docker, который уже запущен как отдельный процесс.',
    'Через них настройки соединения с БД передаются снаружи, поэтому менять образ не требуется и его проще переносить.',
    'Добавить пользователя в группу docker командой sudo usermod -aG docker $USER, затем выполнить newgrp docker.',
]
if index == 1:
    answers = [
        'Квадрат двучлена равен квадрату первого слагаемого, плюс или минус удвоенное произведение, плюс квадрат второго.',
        'Для любого числа, кроме нуля, при степени ноль получится единица.',
        'Если основание возвести в логарифм числа по этому основанию, вернётся само число b.',
        'При одном и том же угле сумма квадратов синуса и косинуса равна единице.',
        'Тангенс — это синус того же угла, делённый на его косинус.',
    ]
report = {'source': source.name, 'method': 'hand-written paraphrases; wall-clock time', 'results': []}
with httpx.Client(timeout=120) as client:
    for card, answer in zip(case['generation']['response']['cards'], answers):
        started = time.perf_counter()
        try:
            response = client.post('https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/v1/ai/answer-reviews', headers={'X-User-ID': case['user_alias']}, json={'session_id': case['session']['response']['session_id'], 'card': card, 'student_answer': answer})
            item = {'question': card['question'], 'answer': answer, 'wall_ms': round((time.perf_counter()-started)*1000), 'status': response.status_code, 'response': response.json()}
        except Exception as exc:
            item = {'question': card['question'], 'answer': answer, 'error': type(exc).__name__, 'wall_ms': round((time.perf_counter()-started)*1000)}
        report['results'].append(item)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        time.sleep(6)

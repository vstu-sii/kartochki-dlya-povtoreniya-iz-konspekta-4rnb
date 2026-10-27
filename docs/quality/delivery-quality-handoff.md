# Delivery → Quality: Lab 5 final handoff

Дата подготовки: 27.10.2026. Этот файл является единым индексом доказательств.
Незаполненные пункты не считаются выполненными и будут обновлены после CI и deploy.

## Интегрированная версия

- ветка: `lab5-integrated-quality`;
- включает Delivery `d49a42e`, AI `9d29cf2` и Quality `9685b3e`;
- конфликты отчётов разрешены в пользу Quality; исполняемые AI-тесты сохранены;
- полный SHA: будет зафиксирован после финального evidence commit.

## Автоматические проверки

- локально: 62/62 unit/integration tests — success;
- локально: 8/8 групп полного набора, 132/132 уникальных кейса — success;
- GitHub Actions run и его артефакты: ожидаются после push;
- новый релизный тег: ожидается только после зелёного branch CI.

## Grafana

- реальный screenshot: ожидается из `grafana-evidence` после запуска Compose;
- ожидаемый путь: `docs/quality/evidence/lab5/grafana-integrated.png`;
- metadata: `docs/quality/evidence/lab5/grafana-integrated.json`;
- production Grafana URL отсутствует: Render разворачивает одноконтейнерный API, поэтому доказательство снимается с идентичного интегрированного Compose-стенда. Это ограничение указано явно.

## Production и Gemini

- URL: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com;
- до новой выкладки `/health` возвращает старую Delivery-версию;
- последний проверочный provider-вызов завершился fallback с `gemini_http_503`;
- production upload, persistence, answer review и серия Gemini без fallback пока не завершены;
- секрет `GEMINI_API_KEY` в handoff и Git не записывается.

## Незавершённое

1. Зелёный интеграционный CI и скачивание его артефактов.
2. Deploy общего SHA и проверка `commit_sha` в `/health`.
3. Обычный PDF и PDF с формулами: HTTP 201 на production.
4. Полный Gemini-сценарий без fallback и повторная серия для p95.
5. Новый неизменяемый tag и полный quality run именно на нём.

# Monitoring: metrics, logs and LLM traces

```bash
docker compose up -d --build --wait
```

- Grafana: `http://localhost:3001` (`GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`).
- Prometheus: `http://localhost:9090`.
- Existing trace viewer: `http://localhost:3000`.

Dashboard `Flashcards production overview` is provisioned automatically. It shows request/error metrics, budget degradation/rejections, Docker service logs and redacted `llm_trace` events. Prompt and PDF contents are not logged unless `TRACE_CONTENT=true`; production keeps it false.

`TokenBudgetAnomaly` fires after repeated cheap-tier transitions; `TokenBudgetRejected` fires on the first rejected request. Both events are also structured JSON in Loki.

export default defineConfig({
  source: {
    type: "plantuml",
    path: "./docs/architecture/c4-container.puml",
  },
  rules: {
    acyclic: true,            // связи контейнеров направлены без циклов
    acl: true,                // Telegram и Gemini доступны только через ACL-адаптеры
    dbPerService: true,       // PostgreSQL принадлежит только Data Service
    commonReuse: true,        // зависимости направлены на узкие контракты

    cohesion: false,          // в MVP один bounded context; сравнивать границы пока нечего
    stableDependencies: false,// стабильность контейнеров ещё не размечена данными изменений
    apiGateway: false,        // публичного REST API нет; вход идёт через Telegram Adapter
  },
});

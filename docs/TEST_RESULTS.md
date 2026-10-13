# Проверки текущего прохода — 9 октября 2026

Python 3.13.16, Django 6.0.9. Настоящий Gemini: **0 вызовов**, ключ отсутствует. Базы и контакты синтетические.

| Проверка | Реальный результат | Доказательство |
|---|---|---|
| Загруженный исходный архив | 51 тест, 2 падения устаревшего source label | REVERIFY-BASELINE.log |
| Найденный исправленный кандидат до новых изменений | 110 тестов, OK | REVERIFY-TEST.log |
| Новые регрессии до исправления | Все 4 падали | REVERIFY-RECOVERY-BEFORE.log |
| Финальная регрессия после B24–B26 | 116 тестов, OK, 21.198 секунды | REVERIFY-FINAL-TEST.log |
| Django system check / migration drift | No issues / No changes detected | Проверено после миграции 0005 |
| Original → миграция 0005 | Компания, диалог, сообщение и заявка сохранены | REVERIFY-MIGRATION.log |
| SQLite, 8 потоков, 80 запросов | 80 HTTP 200, 160 сообщений, 80 полных пар; median 89.87ms, p95 346.18ms | REVERIFY-CONCURRENCY.json |
| 4 одновременных принятия приглашения | Один owner; 1 HTTP 302, 3 HTTP 410 | REVERIFY-RACES.json |
| 4 конфликтующих подтверждения | Ровно одна подтверждённая заявка | REVERIFY-RACES.json |
| Одновременные ходы одного диалога | Второй отклонён; одна пара сообщений | REVERIFY-RACES.json |
| Настоящий SDK, синтетический HTTP localhost | Ответ/18 токенов; 429, пустой ответ и timeout → fallback; по одной попытке | REVERIFY-SDK.json |
| Chromium desktop / 390px | Каталог, reload истории, вход владельца и CRM работают; нет JS ошибок и overflow | REVERIFY-UI.json; reverify-*.png |
| Ruff F401/F541/F841 | Passed; не полный набор правил | REVERIFY-LINT.log |
| Совместимость установленных зависимостей | 31 пакет совместим | REVERIFY-DEPENDENCY-CHECK.log |
| pip-audit по requirements | Known vulnerabilities not found на момент проверки | REVERIFY-DEPENDENCIES.json |
| Production settings check | Два осознанно не включённых HSTS subdomain/preload предупреждения | REVERIFY-DEPLOY-PRODUCTION.log |
| Живой AI | Не выполнен: нет ключа | evaluate_ai --live, missing-key |

Средний response time выше — без Gemini. Он не описывает задержку живого консультанта. Локальная конкуренция не доказывает пригодность SQLite для 100 компаний или нескольких серверов. Отсутствие известных CVE не гарантирует отсутствие всех уязвимостей.

В AI_EVAL_CORPUS.json подготовлены 36 вопросов с ожидаемым поведением для ресторана, магазина и салона. Они **не прогнаны на живой модели** и не являются оценкой качества.

Повторить: установить requirements в отдельном окружении, сохранить существующую .env, затем migrate, check, test. scripts/qa_concurrency.py, qa_races.py и qa_sdk_transport.py используют собственные временные базы. Для живого smoke: отдельная база через NEXORA_DATABASE_PATH, migrate, evaluate_ai --live --max-calls 6. Ключ остаётся в локальной .env.

Старые логи без REVERIFY сохранены как исторические материалы кандидата. Текущие результаты выше имеют приоритет.

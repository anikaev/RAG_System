# RAG Tutor API

Backend-проект для tutoring/RAG-системы по ЕГЭ информатике. Репозиторий собирает в одном сервисе:

- контролируемые подсказки вместо готовых решений;
- retrieval по базе знаний;
- semantic search через `pgvector`;
- проверку Python-кода;
- загрузку документов в knowledge base;
- demo UI для проверки всего потока руками.

Проект не пытается быть универсальным чат-ботом. Основная цель здесь другая: сделать безопасное API-ядро, которое можно использовать как backend для учебного продукта.

## Что умеет сейчас

- `GET /health`
- `GET /metrics`
- `GET /playground`
- `GET /openapi.json`
- `POST /v1/chat/respond`
- `POST /v1/code/check`
- `POST /v1/retrieval/debug`
- `POST /v1/kb/documents`
- `GET /v1/kb/documents`
- `GET /v1/kb/documents/{document_id}`
- `DELETE /v1/kb/documents/{document_id}`

Функционально это покрывает:

- tutoring-ответы с mode-based orchestration;
- `hint_level` progression;
- refusal на запросы полного решения;
- code feedback и отдельный `code/check`;
- DB-first knowledge ingestion;
- lexical и semantic retrieval;
- structured logs, audit events и базовые runtime metrics;
- встроенный UI для демонстрации chat, retrieval, code-check и KB ingestion.

## Технологии

- Python 3.12
- FastAPI
- Pydantic / pydantic-settings
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- `pgvector`
- Redis
- Docker / Docker Compose
- `uv`
- `pytest`
- `mypy`

## Архитектура

### Слои

- `app/api/`  
  HTTP-роуты, transport-level contracts, demo UI.

- `app/core/`  
  Конфиг, middleware, security helpers, policies, logging, audit, metrics.

- `app/services/`  
  Оркестрация chat/code flow, hint progression, ingestion, session logic.

- `app/providers/`  
  LLM, embeddings, retrieval, cache и code execution backends.

- `app/db/`  
  SQLAlchemy models, Alembic migrations, repositories, bootstrap.

- `app/kb/`  
  Chunking, cleaners, ingest pipeline и demo seed documents.

### Главные runtime-компоненты

- `DialogueOrchestrator`  
  Собирает retrieval, hinting, LLM generation и code-feedback в единый chat flow.

- `HintService`  
  Выбирает режим ответа и контролирует силу подсказки.

- `LLMService`  
  Вызывает primary LLM provider, валидирует ответ и уходит в fallback, если ответ небезопасный.

- `KnowledgeIngestionService`  
  Принимает raw document, режет его на chunks, считает embeddings и сохраняет в БД.

- `CodeService`  
  Проверяет код, запускает runner и возвращает структурированный feedback.

## Demo UI

Основная точка входа для ручной проверки:

- `http://127.0.0.1:8000/playground`

Что есть в UI:

- `Tutor Studio`  
  запрос к `chat/respond`, диагностика режима, fallback и used contexts;

- `Retrieval Lens`  
  ручной вызов `retrieval/debug` с просмотром найденных chunks;

- `Code Check`  
  отдельный вызов `code/check` с показом syntax issues, runner status и tests summary;

- `Knowledge Base Studio`  
  загрузка документов в БД и список knowledge documents;

- `Runtime`  
  текущий retriever, providers, session backend и in-memory metrics.

Также `/` редиректит на `/playground`.

## Как это работает

Упрощённый flow для tutoring-запроса:

1. запрос приходит в FastAPI;
2. middleware назначает `request_id`, пишет structured logs и latency;
3. retriever достаёт релевантные chunks;
4. `HintService` выбирает режим ответа;
5. `LLMService` генерирует безопасный ответ;
6. история сохраняется в session store;
7. API возвращает единый JSON envelope.

Flow для knowledge ingestion:

1. документ загружается через `POST /v1/kb/documents`;
2. текст нормализуется и режется на chunks;
3. embeddings считаются через embedding provider;
4. документ и chunks сохраняются в БД;
5. retriever начинает использовать новый контент без правки репозитория.

## Быстрый старт

### Локально

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

После этого открывай:

- `http://127.0.0.1:8000/playground`
- `http://127.0.0.1:8000/docs`

### С PostgreSQL

```bash
export RAG_SESSION_BACKEND=database
export RAG_DATABASE_FALLBACK_TO_MEMORY=false
export RAG_POSTGRES_URL=postgresql+psycopg://rag:rag@127.0.0.1:5432/rag

uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

### Через Docker Compose

```bash
docker compose up --build
```

Compose поднимает:

- `postgres`
- `redis`
- `app`

По умолчанию в compose используется Postgres-образ с `pgvector`.

## Knowledge Base

### Demo seed

В проекте есть demo knowledge base:

- `app/kb/seed/loops_basics.md`
- `app/kb/seed/task_27_arrays.md`

Она нужна для локального bootstrap и резервного fallback path.

### Product path

Основной сценарий уже DB-first:

- документы живут в `knowledge_documents`;
- chunks живут в `knowledge_chunks`;
- новые материалы можно загружать через API;
- retrieval может работать по реально загруженной базе, а не только по `app/kb/seed`.

### Пример загрузки документа

```bash
curl -X POST http://127.0.0.1:8000/v1/kb/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Prefix sums intro",
    "content": "Префиксные суммы позволяют быстро отвечать на запросы суммы на отрезке.\n\nСначала строится массив накопленных сумм.\n\nПотом результат получается как разность двух значений.",
    "subject": "informatics",
    "topic": "prefix_sums",
    "task_id": "prefix-demo",
    "metadata_json": {
      "difficulty": "basic"
    }
  }'
```

## Retrieval modes

В проекте есть несколько retrieval paths:

- `fallback`  
  файловый lexical retrieval по `app/kb/seed`;

- `database_lexical`  
  lexical retrieval по chunks из БД;

- `pgvector`  
  semantic retrieval по embedding vectors.

Если `pgvector` или embeddings provider недоступны, система может откатиться на lexical fallback.

## LLM modes

Сейчас поддерживаются два режима:

- `mock`  
  детерминированный локальный режим для тестов и безопасной отладки;

- `compatible_api`  
  любой OpenAI-compatible HTTP backend, включая self-hosted open-source модели и Hugging Face Router.

### Open-source LLM через compatible API

```bash
export RAG_LLM_PROVIDER_MODE=compatible_api
export RAG_LLM_API_BASE_URL=http://127.0.0.1:8001/v1
export RAG_LLM_MODEL_NAME=your-model-name
export RAG_LLM_API_KEY=optional_token
```

### Hugging Face Router

```bash
export HF_TOKEN=hf_xxx
export RAG_LLM_PROVIDER_MODE=compatible_api
export RAG_LLM_API_BASE_URL=https://router.huggingface.co/v1
export RAG_LLM_MODEL_NAME=openai/gpt-oss-120b:fireworks-ai
export RAG_LLM_RESPONSE_FORMAT_MODE=json_schema
```

## Embeddings и semantic retrieval

Для semantic retrieval можно использовать Jina:

```bash
export JINA_API_KEY=jina_xxx
export RAG_EMBEDDING_PROVIDER_MODE=jina
export RAG_EMBEDDING_API_URL=https://api.jina.ai/v1/embeddings
export RAG_EMBEDDING_MODEL_NAME=jina-embeddings-v3
export RAG_RETRIEVER_BACKEND_MODE=pgvector
export RAG_RETRIEVER_FALLBACK_TO_LEXICAL=true
```

Если среда требует кастомный CA bundle:

```bash
export RAG_EMBEDDING_CA_BUNDLE_PATH=/path/to/corporate-ca.pem
```

Только для локальной отладки:

```bash
export RAG_EMBEDDING_SSL_VERIFY=false
```

## Code execution

Есть два режима:

- `stub`  
  безопасный demo mode без реального sandbox execution;

- `docker`  
  изолированный Docker runner.

### Включить Docker runner

```bash
docker build -f docker/runner-python.Dockerfile -t rag-python-runner:latest .
export RAG_CODE_EXECUTION_BACKEND_MODE=docker
uv run uvicorn app.main:app --reload
```

Runner:

- запускает код в отдельном контейнере;
- не использует сеть;
- ограничивает CPU и память;
- режет timeout;
- блокирует опасные паттерны ещё до запуска.

## Redis

Redis сейчас используется как retrieval cache.

Если Redis доступен:

- retriever кеширует результаты поиска;
- повторные запросы могут отрабатывать быстрее.

Если Redis недоступен:

- сервис не падает;
- автоматически включается `NoOpRetrievalCache`.

## API quick checks

### Health

```bash
curl http://127.0.0.1:8000/health
```

### Metrics

```bash
curl http://127.0.0.1:8000/metrics
```

### Retrieval debug

```bash
curl -X POST http://127.0.0.1:8000/v1/retrieval/debug \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Объясни, как работает цикл for в Python",
    "task_context": {
      "subject": "informatics"
    },
    "top_k": 3
  }'
```

### Chat respond

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/respond \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user",
    "message": "Объясни, как работает цикл for в Python",
    "task_context": {
      "subject": "informatics"
    }
  }'
```

### Code check

```bash
curl -X POST http://127.0.0.1:8000/v1/code/check \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user",
    "language": "python",
    "task_id": "demo-sum",
    "code": "a, b = map(int, input().split())\nprint(a + b)"
  }'
```

## CLI

После установки зависимостей доступны команды:

```bash
uv run rag-cli health
uv run rag-cli chat "Объясни массивы в задаче 27"
uv run rag-cli code-check --code "print(1)"
uv run rag-cli ingest-kb --dry-run
```

## Проверка качества

```bash
uv run pytest
uv run mypy
```

## Структура проекта

```text
app/
  api/
  core/
  db/
  kb/
  providers/
  schemas/
  services/
  tests/
cli/
docker/
```

## Ограничения текущего состояния

- metrics пока in-memory;
- Redis пока не используется как очередь или persistent session layer;
- sandbox runner ещё не рассчитан на multi-tenant production;
- качество tutoring-ответов сильно зависит от подключённого LLM backend;
- semantic retrieval требует рабочий embeddings provider и Postgres с `pgvector`;
- seed KB маленькая и нужна в основном для demo.

## Что дальше

- расширять KB и ingestion;
- улучшать evaluation loop;
- усиливать observability;
- отделять demo UI от inline HTML в сторону нормального frontend слоя.

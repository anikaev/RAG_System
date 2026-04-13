from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(tags=["playground"])


PLAYGROUND_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RAG Tutor Studio</title>
  <style>
    :root {
      --bg: #f6f0e6;
      --paper: rgba(255, 252, 247, 0.9);
      --paper-strong: #fffdf9;
      --ink: #18202a;
      --muted: #5e6976;
      --line: rgba(43, 56, 69, 0.12);
      --accent: #1e7066;
      --accent-strong: #0f4f4a;
      --accent-soft: rgba(30, 112, 102, 0.1);
      --gold: #b9872f;
      --rose: #8b4c5d;
      --ok: #1d7a46;
      --warn: #8a5410;
      --danger: #9f2d3a;
      --shadow: 0 28px 70px rgba(24, 32, 42, 0.11);
      --radius-lg: 28px;
      --radius-md: 18px;
      --radius-sm: 12px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(255, 209, 102, 0.24), transparent 28%),
        radial-gradient(circle at top right, rgba(43, 170, 153, 0.16), transparent 26%),
        linear-gradient(180deg, #fbf7f1 0%, var(--bg) 58%, #efe5d8 100%);
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.16) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.12) 1px, transparent 1px);
      background-size: 36px 36px;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.28), transparent 78%);
    }

    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 28px 20px 56px;
      position: relative;
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(360px, 1fr);
      gap: 20px;
      margin-bottom: 20px;
    }

    .hero-copy,
    .hero-runtime,
    .panel {
      background: var(--paper);
      border: 1px solid rgba(255, 255, 255, 0.66);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
    }

    .hero-copy {
      padding: 28px;
      position: relative;
      overflow: hidden;
    }

    .hero-copy::after {
      content: "";
      position: absolute;
      width: 280px;
      height: 280px;
      top: -120px;
      right: -80px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(30, 112, 102, 0.24), transparent 70%);
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid rgba(30, 112, 102, 0.16);
      color: var(--accent-strong);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 12px;
      font-weight: 700;
    }

    h1, h2, h3 {
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      margin: 0;
      line-height: 1.04;
    }

    h1 {
      font-size: clamp(2.3rem, 4.4vw, 4.6rem);
      margin-top: 18px;
      max-width: 10ch;
    }

    .hero-copy p {
      max-width: 62ch;
      margin: 18px 0 0;
      color: var(--muted);
      line-height: 1.65;
      font-size: 1.02rem;
      position: relative;
      z-index: 1;
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
      position: relative;
      z-index: 1;
    }

    .chip {
      border: 1px solid rgba(24, 32, 42, 0.12);
      background: rgba(255, 255, 255, 0.75);
      color: var(--ink);
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }

    .chip:hover {
      transform: translateY(-1px);
      border-color: rgba(30, 112, 102, 0.28);
      background: white;
    }

    .hero-runtime {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .hero-runtime h2 {
      font-size: 1.7rem;
    }

    .runtime-grid,
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .metric-card {
      padding: 14px 16px;
      border-radius: var(--radius-md);
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
      min-height: 92px;
    }

    .metric-label {
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .metric-value {
      margin-top: 10px;
      font-size: 1.5rem;
      font-weight: 700;
    }

    .metric-note {
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(24, 32, 42, 0.1);
      background: rgba(255, 255, 255, 0.78);
      font-size: 0.92rem;
      color: var(--ink);
    }

    .pill.ok {
      background: rgba(29, 122, 70, 0.1);
      border-color: rgba(29, 122, 70, 0.14);
      color: var(--ok);
    }

    .pill.warn {
      background: rgba(185, 135, 47, 0.12);
      border-color: rgba(185, 135, 47, 0.16);
      color: var(--warn);
    }

    .pill.danger {
      background: rgba(159, 45, 58, 0.1);
      border-color: rgba(159, 45, 58, 0.16);
      color: var(--danger);
    }

    .dashboard {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.92fr);
      gap: 20px;
      align-items: start;
    }

    .stack {
      display: grid;
      gap: 20px;
    }

    .panel {
      padding: 24px;
      animation: rise 320ms ease;
    }

    @keyframes rise {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: end;
      margin-bottom: 18px;
    }

    .section-head h2 {
      font-size: 2rem;
    }

    .section-head p,
    .panel p {
      margin: 6px 0 0;
      color: var(--muted);
      line-height: 1.55;
    }

    .controls-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }

    .split-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 0.92fr);
      gap: 18px;
    }

    .kb-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.12fr) minmax(300px, 0.88fr);
      gap: 18px;
    }

    label {
      display: block;
      font-size: 0.85rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 7px;
      font-weight: 700;
    }

    input,
    textarea,
    select,
    button {
      width: 100%;
      border-radius: var(--radius-sm);
      font: inherit;
    }

    input,
    textarea,
    select {
      border: 1px solid rgba(24, 32, 42, 0.12);
      background: rgba(255, 255, 255, 0.86);
      padding: 13px 14px;
      color: var(--ink);
      transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }

    textarea {
      resize: vertical;
      min-height: 120px;
    }

    input:focus,
    textarea:focus,
    select:focus {
      outline: none;
      border-color: rgba(30, 112, 102, 0.36);
      box-shadow: 0 0 0 4px rgba(30, 112, 102, 0.08);
    }

    .editor-large {
      min-height: 170px;
    }

    .editor-code {
      min-height: 220px;
      font-family: "SFMono-Regular", "JetBrains Mono", "Menlo", monospace;
      font-size: 0.94rem;
      line-height: 1.55;
    }

    .action-row {
      display: flex;
      gap: 10px;
      margin-top: 16px;
      flex-wrap: wrap;
    }

    button {
      border: 0;
      cursor: pointer;
      padding: 13px 16px;
      font-weight: 700;
      transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
    }

    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 12px 26px rgba(24, 32, 42, 0.14);
    }

    button:active {
      transform: translateY(0);
    }

    .button-primary {
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
      color: white;
    }

    .button-secondary {
      background: rgba(255, 255, 255, 0.76);
      border: 1px solid rgba(24, 32, 42, 0.12);
      color: var(--ink);
    }

    .status-strip {
      min-height: 24px;
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.95rem;
    }

    .panel-surface {
      margin-top: 18px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: rgba(255, 255, 255, 0.72);
      padding: 18px;
    }

    .result-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }

    .muted-text {
      color: var(--muted);
      font-size: 0.95rem;
    }

    .answer-card,
    .guide-card,
    .context-card,
    .issue-card,
    .doc-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.78);
    }

    .guide-card {
      background: linear-gradient(135deg, rgba(30, 112, 102, 0.08), rgba(255, 255, 255, 0.94));
    }

    .answer-text,
    .code-output {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      line-height: 1.68;
    }

    .result-list,
    .document-list,
    .issue-list {
      display: grid;
      gap: 12px;
    }

    .context-title,
    .doc-title,
    .issue-title {
      font-weight: 700;
      margin-bottom: 8px;
    }

    .context-body,
    .doc-body {
      margin: 0;
      color: var(--muted);
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.58;
    }

    .issue-line {
      color: var(--muted);
      font-size: 0.92rem;
      margin-top: 6px;
    }

    .empty-state {
      border: 1px dashed rgba(24, 32, 42, 0.16);
      border-radius: 18px;
      padding: 20px;
      color: var(--muted);
      text-align: center;
      background: rgba(255, 255, 255, 0.52);
    }

    .helper-text {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .danger-button {
      background: rgba(159, 45, 58, 0.08);
      color: var(--danger);
      border: 1px solid rgba(159, 45, 58, 0.16);
    }

    details {
      margin-top: 14px;
    }

    summary {
      cursor: pointer;
      color: var(--muted);
      font-weight: 700;
    }

    .tiny-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }

    .tiny-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(255, 255, 255, 0.7);
    }

    .tiny-card strong {
      display: block;
      margin-bottom: 6px;
    }

    @media (max-width: 1180px) {
      .hero,
      .dashboard,
      .split-grid,
      .kb-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 840px) {
      main {
        padding: 18px 14px 36px;
      }

      .controls-grid,
      .runtime-grid,
      .metric-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .panel,
      .hero-copy,
      .hero-runtime {
        padding: 18px;
        border-radius: 22px;
      }

      .section-head {
        flex-direction: column;
        align-items: start;
      }
    }

    @media (max-width: 560px) {
      .controls-grid,
      .runtime-grid,
      .metric-grid,
      .tiny-grid {
        grid-template-columns: 1fr;
      }

      h1 {
        max-width: 12ch;
      }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">RAG Tutor Demo UI</div>
        <h1>Semantic tutoring console</h1>
        <p>
          Один экран для проверки всего потока: retrieval, tutoring-ответа, code check и загрузки
          документов в knowledge base. Здесь уже видно, на каких чанках строится ответ и был ли
          реальный LLM-ответ или fallback.
        </p>
        <div class="chip-row">
          <button class="chip" data-preset="loops">Цикл for и инвариант</button>
          <button class="chip" data-preset="task27">Задача 27 и агрегаты</button>
          <button class="chip" data-preset="code">Синтаксическая ошибка в Python</button>
        </div>
      </div>

      <aside class="hero-runtime">
        <div>
          <h2>Runtime</h2>
          <p>Здесь видно, какой backend реально поднят, готов ли retriever и как живёт runtime.</p>
        </div>
        <div id="runtime-pills" class="pill-row"></div>
        <div class="runtime-grid">
          <div class="metric-card">
            <div class="metric-label">Configured Retriever</div>
            <div id="runtime-configured-retriever" class="metric-value">-</div>
            <div id="runtime-retriever-status" class="metric-note">-</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Model Stack</div>
            <div id="runtime-model-stack" class="metric-value">-</div>
            <div id="runtime-code-backend" class="metric-note">-</div>
          </div>
        </div>
        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-label">Requests</div>
            <div id="metric-requests" class="metric-value">-</div>
            <div id="metric-latency" class="metric-note">-</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Code Runs</div>
            <div id="metric-code-runs" class="metric-value">-</div>
            <div id="metric-code-latency" class="metric-note">-</div>
          </div>
        </div>
      </aside>
    </section>

    <section class="dashboard">
      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Tutor Studio</h2>
            <p>Главный поток проверки продукта: question → retrieval → orchestration → answer.</p>
          </div>
        </div>

        <div class="controls-grid">
          <div>
            <label for="subject">Subject</label>
            <input id="subject" value="informatics" />
          </div>
          <div>
            <label for="topic">Topic</label>
            <input id="topic" value="" placeholder="например task_27" />
          </div>
          <div>
            <label for="task-id">Task ID</label>
            <input id="task-id" value="" placeholder="например demo-sum" />
          </div>
          <div>
            <label for="top-k">Top K</label>
            <select id="top-k">
              <option value="3" selected>3</option>
              <option value="4">4</option>
              <option value="5">5</option>
              <option value="6">6</option>
            </select>
          </div>
        </div>

        <div class="split-grid" style="margin-top: 18px;">
          <div>
            <label for="chat-message">Запрос к тьютору</label>
            <textarea id="chat-message" class="editor-large">Объясни, как работает цикл for в Python</textarea>
          </div>
          <div>
            <label for="retrieval-query">Запрос для retrieval debug</label>
            <textarea id="retrieval-query">Объясни, как работает цикл for в Python</textarea>
          </div>
        </div>

        <div class="controls-grid" style="margin-top: 14px;">
          <div>
            <label for="session-id">Session ID</label>
            <input id="session-id" value="" placeholder="пусто = новая сессия" />
          </div>
          <div>
            <label for="user-id">User ID</label>
            <input id="user-id" value="demo-user" />
          </div>
          <div style="grid-column: span 2;">
            <label>&nbsp;</label>
            <div class="action-row" style="margin-top: 0;">
              <button id="send-chat" class="button-primary">Спросить тьютора</button>
              <button id="run-retrieval" class="button-secondary">Проверить retrieval</button>
              <button id="sync-query" class="button-secondary">Скопировать вопрос в retrieval</button>
            </div>
          </div>
        </div>

        <div id="chat-status" class="status-strip"></div>

        <div class="panel-surface">
          <div class="result-head">
            <div>
              <div class="metric-label">Ответ</div>
              <div id="chat-summary" class="muted-text">Пока ничего не отправлено.</div>
            </div>
            <div id="chat-badges" class="pill-row"></div>
          </div>
          <div class="answer-card">
            <pre id="chat-response" class="answer-text">Здесь появится ответ тьютора.</pre>
          </div>
          <div class="guide-card" style="margin-top: 12px;">
            <div class="metric-label">Наводящий вопрос</div>
            <div id="chat-guiding-question" class="answer-text">-</div>
          </div>
          <details>
            <summary>Диагностика RAG и LLM</summary>
            <div id="chat-diagnostics" class="tiny-grid"></div>
          </details>
        </div>
      </section>

      <aside class="stack">
        <section class="panel">
          <div class="section-head">
            <div>
              <h2>Retrieval Lens</h2>
              <p>Показывает, какой backend сработал и какие чанки реально пришли в orchestrator.</p>
            </div>
          </div>
          <div id="retrieval-status" class="status-strip"></div>
          <div class="panel-surface">
            <div class="result-head">
              <div>
                <div class="metric-label">Результат поиска</div>
                <div id="retrieval-summary" class="muted-text">Пока пусто.</div>
              </div>
              <div id="retrieval-badges" class="pill-row"></div>
            </div>
            <div id="retrieval-results" class="result-list">
              <div class="empty-state">Сначала запусти retrieval или отправь один из demo-пресетов.</div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="section-head">
            <div>
              <h2>Code Check</h2>
              <p>Отдельная проверка `code/check`: syntax, sandbox status, issues и task-specific tests.</p>
            </div>
          </div>
          <label for="code-input">Python код</label>
          <textarea id="code-input" class="editor-code">def solve(nums):
    total = 0
    for value in nums
        total += value
    return total
</textarea>
          <div class="action-row">
            <button id="run-code-check" class="button-primary">Проверить код</button>
          </div>
          <div id="code-status" class="status-strip"></div>
          <div class="panel-surface">
            <div class="result-head">
              <div>
                <div class="metric-label">Результат проверки</div>
                <div id="code-summary" class="muted-text">Пока пусто.</div>
              </div>
              <div id="code-badges" class="pill-row"></div>
            </div>
            <div class="answer-card">
              <pre id="code-feedback" class="code-output">Здесь появится feedback по коду.</pre>
            </div>
            <details>
              <summary>Ошибки и тесты</summary>
              <div id="code-details" class="issue-list" style="margin-top: 12px;"></div>
            </details>
          </div>
        </section>
      </aside>
    </section>

    <section class="panel" style="margin-top: 20px;">
      <div class="section-head">
        <div>
          <h2>Knowledge Base Studio</h2>
          <p>Загрузка документов в БД без правки `app/kb/seed`, чтобы сразу проверить ingestion и retrieval.</p>
        </div>
      </div>
      <div class="kb-grid">
        <div>
          <div class="controls-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 0;">
            <div>
              <label for="kb-title">Title</label>
              <input id="kb-title" value="Prefix sums intro" />
            </div>
            <div>
              <label for="kb-source-type">Source Type</label>
              <input id="kb-source-type" value="manual" />
            </div>
          </div>
          <div class="controls-grid" style="grid-template-columns: repeat(3, minmax(0, 1fr));">
            <div>
              <label for="kb-subject">Subject</label>
              <input id="kb-subject" value="informatics" />
            </div>
            <div>
              <label for="kb-topic">Topic</label>
              <input id="kb-topic" value="prefix_sums" />
            </div>
            <div>
              <label for="kb-task-id">Task ID</label>
              <input id="kb-task-id" value="prefix-demo" />
            </div>
          </div>
          <label for="kb-content" style="margin-top: 16px;">Document Content</label>
          <textarea id="kb-content" class="editor-large">Префиксные суммы позволяют быстро отвечать на запросы суммы на отрезке.

Сначала строится массив накопленных сумм.

Потом результат получается как разность двух значений.</textarea>
          <div class="action-row">
            <button id="create-document" class="button-primary">Загрузить в knowledge base</button>
            <button id="refresh-documents" class="button-secondary">Обновить список</button>
          </div>
          <div id="kb-status" class="status-strip"></div>
        </div>

        <div class="panel-surface" style="margin-top: 0;">
          <div class="result-head">
            <div>
              <div class="metric-label">Документы в БД</div>
              <div id="kb-summary" class="muted-text">Пока пусто.</div>
            </div>
          </div>
          <div id="kb-documents" class="document-list">
            <div class="empty-state">Список документов появится после первой загрузки.</div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <script>
    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        const reason = payload?.error?.message || response.statusText;
        throw new Error(reason);
      }
      return payload.data;
    }

    function setStatus(elementId, message, tone = "neutral") {
      const element = document.getElementById(elementId);
      element.textContent = message;
      element.style.color =
        tone === "danger" ? "var(--danger)" :
        tone === "warn" ? "var(--warn)" :
        tone === "ok" ? "var(--ok)" :
        "var(--muted)";
    }

    function taskContext() {
      const subject = document.getElementById("subject").value.trim() || "informatics";
      const topic = document.getElementById("topic").value.trim();
      const taskId = document.getElementById("task-id").value.trim();
      return {
        subject,
        topic: topic || null,
        task_id: taskId || null,
      };
    }

    function renderPills(containerId, items) {
      const container = document.getElementById(containerId);
      container.innerHTML = items
        .filter((item) => item && item.label)
        .map((item) => {
          const tone = item.tone ? ` ${item.tone}` : "";
          return `<span class="pill${tone}">${escapeHtml(item.label)}</span>`;
        })
        .join("");
    }

    function formatNumber(value, fractionDigits = 1) {
      return Number.isFinite(value) ? value.toFixed(fractionDigits) : "-";
    }

    async function refreshRuntime() {
      try {
        const [health, metrics] = await Promise.all([
          fetchJson("/health"),
          fetchJson("/metrics"),
        ]);
        renderPills("runtime-pills", [
          {label: `status ${health.status}`, tone: "ok"},
          {label: `session ${health.session_backend || "-"}`},
          {label: `retriever ${health.retriever_backend || "-"}`, tone: health.retriever_ready ? "ok" : "warn"},
          {label: `embedding ${health.embedding_provider || "-"}`},
          {label: `llm ${health.llm_provider || "-"}`},
        ]);
        document.getElementById("runtime-configured-retriever").textContent =
          health.configured_retriever_backend || "-";
        document.getElementById("runtime-retriever-status").textContent =
          health.retriever_status || (health.retriever_ready ? "Retriever ready" : "Retriever degraded");
        document.getElementById("runtime-model-stack").textContent =
          `${health.embedding_provider || "-"} / ${health.llm_provider || "-"}`;
        document.getElementById("runtime-code-backend").textContent =
          `Code backend: ${health.code_execution_backend || "-"}`;
        document.getElementById("metric-requests").textContent = String(metrics.total_requests);
        document.getElementById("metric-latency").textContent =
          `avg latency ${formatNumber(metrics.avg_latency_ms)} ms`;
        document.getElementById("metric-code-runs").textContent = String(metrics.total_code_executions);
        document.getElementById("metric-code-latency").textContent =
          `avg code latency ${formatNumber(metrics.avg_code_execution_ms)} ms`;
      } catch (error) {
        renderPills("runtime-pills", [{label: `runtime error: ${error.message}`, tone: "danger"}]);
      }
    }

    function renderRetrievalResults(data) {
      renderPills("retrieval-badges", [
        {label: `backend ${data.backend}`, tone: data.ready ? "ok" : "warn"},
        {label: `ready ${data.ready}`},
        data.status ? {label: data.status, tone: "warn"} : null,
        {label: `contexts ${data.context_count}`},
      ]);
      document.getElementById("retrieval-summary").textContent =
        `По запросу найдено ${data.context_count} chunk(s).`;
      const container = document.getElementById("retrieval-results");
      if (data.contexts.length === 0) {
        container.innerHTML = "<div class='empty-state'>Контекст не найден. Попробуй другой запрос или расширь KB.</div>";
        return;
      }
      container.innerHTML = data.contexts.map((item) => {
        const meta = Object.entries(item.metadata || {})
          .filter((entry) => entry[1])
          .map((entry) => `<span class="pill">${escapeHtml(`${entry[0]}=${entry[1]}`)}</span>`)
          .join("");
        return `
          <article class="context-card">
            <div class="result-head">
              <div>
                <div class="context-title">${escapeHtml(item.chunk_id)}</div>
                <div class="muted-text">score ${escapeHtml(item.score.toFixed(3))}</div>
              </div>
              <div class="pill-row">${meta}</div>
            </div>
            <p class="context-body">${escapeHtml(item.content)}</p>
          </article>
        `;
      }).join("");
    }

    async function runRetrieval() {
      const query = document.getElementById("retrieval-query").value.trim();
      setStatus("retrieval-status", "Идёт retrieval...", "neutral");
      try {
        const data = await fetchJson("/v1/retrieval/debug", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            query,
            task_context: taskContext(),
            top_k: Number(document.getElementById("top-k").value),
          }),
        });
        renderRetrievalResults(data);
        setStatus("retrieval-status", "Retrieval отработал.", "ok");
      } catch (error) {
        document.getElementById("retrieval-summary").textContent = "Не удалось получить retrieval.";
        document.getElementById("retrieval-results").innerHTML =
          `<div class="empty-state">${escapeHtml(error.message)}</div>`;
        renderPills("retrieval-badges", [{label: "retrieval error", tone: "danger"}]);
        setStatus("retrieval-status", error.message, "danger");
      } finally {
        await refreshRuntime();
      }
    }

    function buildChatDiagnosticCards(data) {
      const diagnostics = [
        {
          title: "LLM provider",
          value: data.llm_provider || "-",
        },
        {
          title: "Primary provider",
          value: data.llm_primary_provider || "-",
        },
        {
          title: "Fallback",
          value: data.llm_fallback_used ? "yes" : "no",
        },
        {
          title: "Context IDs",
          value: data.used_context_ids.length ? data.used_context_ids.join(", ") : "none",
        },
      ];
      if (data.llm_fallback_reason) {
        diagnostics.push({
          title: "Fallback reason",
          value: data.llm_fallback_reason,
        });
      }
      return diagnostics.map((item) => `
        <div class="tiny-card">
          <strong>${escapeHtml(item.title)}</strong>
          <div class="muted-text">${escapeHtml(item.value)}</div>
        </div>
      `).join("");
    }

    async function sendChat() {
      const message = document.getElementById("chat-message").value.trim();
      const sessionId = document.getElementById("session-id").value.trim();
      const userId = document.getElementById("user-id").value.trim() || "demo-user";
      setStatus("chat-status", "Идёт запрос к chat/respond...", "neutral");
      document.getElementById("chat-response").textContent = "";
      document.getElementById("chat-guiding-question").textContent = "-";
      try {
        const data = await fetchJson("/v1/chat/respond", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            session_id: sessionId || null,
            user_id: userId,
            message,
            task_context: taskContext(),
          }),
        });
        document.getElementById("session-id").value = data.session_id;
        document.getElementById("chat-summary").textContent =
          `mode ${data.mode} · hint level ${data.hint_level} · confidence ${data.confidence.toFixed(2)} · contexts ${data.used_context_ids.length}`;
        renderPills("chat-badges", [
          {label: `mode ${data.mode}`},
          {label: `hint ${data.hint_level}`},
          {label: `confidence ${data.confidence.toFixed(2)}`},
          {label: data.refusal ? "refusal true" : "refusal false", tone: data.refusal ? "warn" : "ok"},
          {label: data.llm_fallback_used ? "fallback used" : "primary answer", tone: data.llm_fallback_used ? "warn" : "ok"},
        ]);
        document.getElementById("chat-response").textContent = data.response_text || "-";
        document.getElementById("chat-guiding-question").textContent = data.guiding_question || "-";
        document.getElementById("chat-diagnostics").innerHTML = buildChatDiagnosticCards(data);
        setStatus("chat-status", "Ответ тьютора получен.", "ok");
      } catch (error) {
        document.getElementById("chat-summary").textContent = "Не удалось получить ответ.";
        document.getElementById("chat-response").textContent = error.message;
        document.getElementById("chat-guiding-question").textContent = "-";
        document.getElementById("chat-diagnostics").innerHTML = "";
        renderPills("chat-badges", [{label: "chat error", tone: "danger"}]);
        setStatus("chat-status", error.message, "danger");
      } finally {
        await refreshRuntime();
      }
    }

    function renderCodeDetails(data) {
      const details = [];
      if (data.issues.length > 0) {
        details.push(...data.issues.map((issue) => `
          <article class="issue-card">
            <div class="issue-title">${escapeHtml(issue.code)} · ${escapeHtml(issue.severity)}</div>
            <div class="muted-text">${escapeHtml(issue.message)}</div>
            <div class="issue-line">
              ${issue.line ? `line ${escapeHtml(issue.line)}${issue.column ? `, column ${escapeHtml(issue.column)}` : ""}` : "line n/a"}
            </div>
          </article>
        `));
      }
      details.push(`
        <article class="tiny-card">
          <strong>Execution summary</strong>
          <div class="muted-text">
            syntax_ok=${escapeHtml(data.summary.syntax_ok)} · execution_status=${escapeHtml(data.summary.execution_status)}
          </div>
        </article>
      `);
      details.push(`
        <article class="tiny-card">
          <strong>Tests</strong>
          <div class="muted-text">
            public ${escapeHtml(data.summary.public_tests_passed)}/${escapeHtml(data.summary.public_tests_total)} · hidden ${escapeHtml(data.summary.hidden_tests_summary)}
          </div>
        </article>
      `);
      return details.join("");
    }

    async function runCodeCheck() {
      const sessionId = document.getElementById("session-id").value.trim();
      const userId = document.getElementById("user-id").value.trim() || "demo-user";
      const taskId = document.getElementById("task-id").value.trim();
      const code = document.getElementById("code-input").value;
      setStatus("code-status", "Идёт code/check...", "neutral");
      try {
        const data = await fetchJson("/v1/code/check", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            session_id: sessionId || null,
            user_id: userId,
            language: "python",
            code,
            task_id: taskId || null,
          }),
        });
        document.getElementById("session-id").value = data.session_id;
        document.getElementById("code-summary").textContent =
          `accepted ${data.accepted} · execution ${data.summary.execution_status} · issues ${data.issues.length}`;
        renderPills("code-badges", [
          {label: data.accepted ? "accepted" : "needs fixes", tone: data.accepted ? "ok" : "warn"},
          {label: `syntax ${data.summary.syntax_ok}`},
          {label: `runner ${data.summary.runner_available}`},
          {label: `public ${data.summary.public_tests_passed}/${data.summary.public_tests_total}`},
        ]);
        document.getElementById("code-feedback").textContent = data.feedback_text || "-";
        document.getElementById("code-details").innerHTML = renderCodeDetails(data);
        setStatus("code-status", "Проверка кода завершена.", "ok");
      } catch (error) {
        document.getElementById("code-summary").textContent = "Не удалось проверить код.";
        document.getElementById("code-feedback").textContent = error.message;
        document.getElementById("code-details").innerHTML = "";
        renderPills("code-badges", [{label: "code error", tone: "danger"}]);
        setStatus("code-status", error.message, "danger");
      } finally {
        await refreshRuntime();
      }
    }

    async function loadDocuments() {
      try {
        const data = await fetchJson("/v1/kb/documents");
        document.getElementById("kb-summary").textContent = `Всего документов: ${data.total}.`;
        const container = document.getElementById("kb-documents");
        if (data.documents.length === 0) {
          container.innerHTML = "<div class='empty-state'>В БД пока нет документов. Загрузи первый текст справа.</div>";
          return;
        }
        container.innerHTML = data.documents.map((doc) => `
          <article class="doc-card">
            <div class="result-head">
              <div>
                <div class="doc-title">${escapeHtml(doc.title)}</div>
                <div class="muted-text">${escapeHtml(doc.document_id)} · ${escapeHtml(doc.status)} · chunks ${escapeHtml(doc.chunk_count)}</div>
              </div>
              <button class="danger-button delete-document" data-document-id="${escapeHtml(doc.document_id)}">Удалить</button>
            </div>
            <div class="pill-row">
              <span class="pill">${escapeHtml(doc.subject)}</span>
              ${doc.topic ? `<span class="pill">${escapeHtml(doc.topic)}</span>` : ""}
              ${doc.task_id ? `<span class="pill">${escapeHtml(doc.task_id)}</span>` : ""}
              <span class="pill">${escapeHtml(doc.source_type)}</span>
            </div>
          </article>
        `).join("");
        container.querySelectorAll(".delete-document").forEach((button) => {
          button.addEventListener("click", async () => {
            await deleteDocument(button.dataset.documentId || "");
          });
        });
      } catch (error) {
        document.getElementById("kb-summary").textContent = "KB management недоступен.";
        document.getElementById("kb-documents").innerHTML =
          `<div class="empty-state">${escapeHtml(error.message)}</div>`;
        setStatus("kb-status", error.message, "warn");
      }
    }

    async function createDocument() {
      setStatus("kb-status", "Идёт загрузка документа...", "neutral");
      try {
        const payload = {
          title: document.getElementById("kb-title").value.trim(),
          content: document.getElementById("kb-content").value,
          subject: document.getElementById("kb-subject").value.trim() || "informatics",
          topic: document.getElementById("kb-topic").value.trim() || null,
          task_id: document.getElementById("kb-task-id").value.trim() || null,
          source_type: document.getElementById("kb-source-type").value.trim() || "manual",
        };
        const data = await fetchJson("/v1/kb/documents", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        setStatus("kb-status", `Документ ${data.document_id} загружен.`, "ok");
        document.getElementById("topic").value = payload.topic || "";
        document.getElementById("task-id").value = payload.task_id || "";
        await loadDocuments();
      } catch (error) {
        setStatus("kb-status", error.message, "danger");
      } finally {
        await refreshRuntime();
      }
    }

    async function deleteDocument(documentId) {
      setStatus("kb-status", `Удаляю ${documentId}...`, "neutral");
      try {
        await fetchJson(`/v1/kb/documents/${encodeURIComponent(documentId)}`, {
          method: "DELETE",
        });
        setStatus("kb-status", `Документ ${documentId} удалён.`, "ok");
        await loadDocuments();
      } catch (error) {
        setStatus("kb-status", error.message, "danger");
      } finally {
        await refreshRuntime();
      }
    }

    function applyPreset(name) {
      if (name === "loops") {
        document.getElementById("chat-message").value = "Объясни, как работает цикл for в Python";
        document.getElementById("retrieval-query").value = "что должно оставаться верным на каждом шаге цикла";
        document.getElementById("topic").value = "";
        document.getElementById("task-id").value = "";
        document.getElementById("code-input").value = `for i in range(3)
    print(i)`;
        return;
      }
      if (name === "task27") {
        document.getElementById("chat-message").value = "Дай ещё подсказку по задаче 27, но без готового решения";
        document.getElementById("retrieval-query").value = "как решать задачу 27 по массивам без полного перебора";
        document.getElementById("topic").value = "task_27";
        document.getElementById("task-id").value = "27-array-scan";
        document.getElementById("code-input").value = `def solve(nums):
    best = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            best = max(best, nums[i] + nums[j])
    return best`;
        return;
      }
      if (name === "code") {
        document.getElementById("chat-message").value = "```python\\nfor i in range(3)\\n    print(i)\\n```";
        document.getElementById("retrieval-query").value = "синтаксическая ошибка в цикле for python";
        document.getElementById("topic").value = "";
        document.getElementById("task-id").value = "demo-sum";
        document.getElementById("code-input").value = `def solve(nums):
    total = 0
    for value in nums
        total += value
    return total`;
      }
    }

    document.getElementById("send-chat").addEventListener("click", sendChat);
    document.getElementById("run-retrieval").addEventListener("click", runRetrieval);
    document.getElementById("run-code-check").addEventListener("click", runCodeCheck);
    document.getElementById("create-document").addEventListener("click", createDocument);
    document.getElementById("refresh-documents").addEventListener("click", loadDocuments);
    document.getElementById("sync-query").addEventListener("click", () => {
      document.getElementById("retrieval-query").value = document.getElementById("chat-message").value.trim();
      setStatus("retrieval-status", "Текст запроса синхронизирован с chat.", "ok");
    });
    document.querySelectorAll("[data-preset]").forEach((button) => {
      button.addEventListener("click", () => {
        applyPreset(button.dataset.preset || "");
      });
    });

    applyPreset("loops");
    refreshRuntime();
    runRetrieval();
    loadDocuments();
  </script>
</body>
</html>
"""


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/playground", status_code=307)


@router.get("/playground", response_class=HTMLResponse, include_in_schema=False)
async def playground() -> HTMLResponse:
    return HTMLResponse(content=PLAYGROUND_HTML)

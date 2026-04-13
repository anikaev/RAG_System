from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["playground"])


PLAYGROUND_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RAG Playground</title>
  <style>
    :root {
      --bg: #f4efe7;
      --panel: #fffdf9;
      --ink: #1f2933;
      --muted: #52606d;
      --accent: #0f766e;
      --border: #d9d1c7;
      --warn: #8a4b08;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      background:
        radial-gradient(circle at top right, #d5f5ef 0, transparent 28%),
        linear-gradient(180deg, #f8f5ee 0%, var(--bg) 100%);
      color: var(--ink);
    }
    main {
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    h1, h2 { margin: 0 0 12px; }
    p { color: var(--muted); }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
      margin-top: 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 14px 40px rgba(31, 41, 51, 0.06);
    }
    .panel-wide { margin-top: 18px; }
    label {
      display: block;
      font-size: 14px;
      margin: 12px 0 6px;
      color: var(--muted);
    }
    input, textarea, button {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 10px 12px;
      font: inherit;
      background: white;
      color: var(--ink);
    }
    textarea { min-height: 140px; resize: vertical; }
    button {
      margin-top: 14px;
      background: var(--accent);
      color: white;
      border: 0;
      cursor: pointer;
      font-weight: 600;
    }
    .subgrid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: #e6fffb;
      color: #0f766e;
      margin-right: 6px;
      margin-bottom: 6px;
      font-size: 13px;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      margin: 0;
      overflow: auto;
    }
    .context-card {
      border-top: 1px solid var(--border);
      padding-top: 12px;
      margin-top: 12px;
    }
    .meta {
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 8px;
    }
    .warn {
      color: var(--warn);
      font-size: 14px;
    }
  </style>
</head>
<body>
  <main>
    <h1>RAG Playground</h1>
    <p>Здесь видно не только ответ модели, но и retrieval backend, readiness и найденные chunks.</p>

    <div class="panel" id="health-panel">
      <h2>Runtime</h2>
      <div id="health-content">Загрузка...</div>
    </div>

    <div class="grid">
      <section class="panel">
        <h2>Retrieval Debug</h2>
        <label for="query">Запрос</label>
        <textarea id="query">Объясни, как работает цикл for в Python</textarea>
        <div class="subgrid">
          <div>
            <label for="subject">Subject</label>
            <input id="subject" value="informatics" />
          </div>
          <div>
            <label for="topic">Topic</label>
            <input id="topic" value="" />
          </div>
          <div>
            <label for="task-id">Task ID</label>
            <input id="task-id" value="" />
          </div>
        </div>
        <button id="run-retrieval">Показать retrieval</button>
        <div class="panel-wide">
          <div id="retrieval-summary" class="meta"></div>
          <div id="retrieval-results"></div>
        </div>
      </section>

      <section class="panel">
        <h2>Chat</h2>
        <label for="session-id">Session ID</label>
        <input id="session-id" value="" placeholder="оставь пустым для новой сессии" />
        <label for="user-id">User ID</label>
        <input id="user-id" value="demo-user" />
        <button id="send-chat">Отправить в chat/respond</button>
        <div class="panel-wide">
          <div id="chat-summary" class="meta"></div>
          <pre id="chat-response">Пока пусто.</pre>
        </div>
      </section>
    </div>
  </main>

  <script>
    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        const reason = payload?.error?.message || response.statusText;
        throw new Error(reason);
      }
      return payload.data;
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

    async function loadHealth() {
      const data = await fetchJson("/health");
      const html = [
        `<span class="badge">status: ${data.status}</span>`,
        `<span class="badge">session: ${data.session_backend}</span>`,
        `<span class="badge">retriever: ${data.retriever_backend}</span>`,
        `<span class="badge">embedding: ${data.embedding_provider}</span>`,
        `<span class="badge">llm: ${data.llm_provider}</span>`,
        `<span class="badge">code: ${data.code_execution_backend}</span>`,
      ].join("");
      const status = data.retriever_status
        ? `<p class="warn">Retriever status: ${data.retriever_status}</p>`
        : "";
      document.getElementById("health-content").innerHTML =
        html + `<p>Configured retriever: ${data.configured_retriever_backend}</p>` + status;
    }

    async function runRetrieval() {
      const query = document.getElementById("query").value.trim();
      const summary = document.getElementById("retrieval-summary");
      const container = document.getElementById("retrieval-results");
      summary.textContent = "Идёт retrieval...";
      container.innerHTML = "";
      try {
        const data = await fetchJson("/v1/retrieval/debug", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            query,
            task_context: taskContext(),
            top_k: 3,
          }),
        });
        summary.textContent =
          `backend=${data.backend}; ready=${data.ready}; contexts=${data.context_count}`;
        if (data.status) {
          summary.textContent += `; status=${data.status}`;
        }
        container.innerHTML = data.contexts.map((item) => `
          <div class="context-card">
            <div class="meta">${item.chunk_id} | score=${item.score.toFixed(3)}</div>
            <pre>${item.content}</pre>
          </div>
        `).join("") || "<p class='warn'>Контекст не найден.</p>";
      } catch (error) {
        summary.textContent = "";
        container.innerHTML = `<p class="warn">${error.message}</p>`;
      }
    }

    async function sendChat() {
      const message = document.getElementById("query").value.trim();
      const sessionId = document.getElementById("session-id").value.trim();
      const userId = document.getElementById("user-id").value.trim() || "demo-user";
      const summary = document.getElementById("chat-summary");
      const responseBox = document.getElementById("chat-response");
      summary.textContent = "Идёт chat/respond...";
      responseBox.textContent = "";
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
        summary.textContent =
          `mode=${data.mode}; hint_level=${data.hint_level}; confidence=${data.confidence}; contexts=${data.used_context_ids.length}`;
        responseBox.textContent =
          `${data.response_text}\n\nused_context_ids: ${JSON.stringify(data.used_context_ids, null, 2)}\n` +
          `guiding_question: ${data.guiding_question || "-"}\nrefusal: ${data.refusal}`;
      } catch (error) {
        summary.textContent = "";
        responseBox.textContent = error.message;
      }
    }

    document.getElementById("run-retrieval").addEventListener("click", runRetrieval);
    document.getElementById("send-chat").addEventListener("click", sendChat);
    loadHealth();
    runRetrieval();
  </script>
</body>
</html>
"""


@router.get("/playground", response_class=HTMLResponse, include_in_schema=False)
async def playground() -> HTMLResponse:
    return HTMLResponse(content=PLAYGROUND_HTML)

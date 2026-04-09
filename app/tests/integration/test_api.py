from __future__ import annotations

from app.db.repositories import ChatMessageRepository, ChatSessionRepository


def test_healthcheck_returns_enveloped_success(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ok"
    assert "request_id" in payload["meta"]
    assert "X-Request-ID" in response.headers


def test_openapi_is_available(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "RAG Tutor API"
    assert "/v1/chat/respond" in payload["paths"]


def test_chat_endpoint_returns_contextual_hint(client):
    response = client.post(
        "/v1/chat/respond",
        json={
            "user_id": "demo-user",
            "message": "Объясни, как работает цикл for в Python",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["mode"] == "concept_explainer"
    assert payload["data"]["used_context_ids"]
    assert payload["data"]["session_id"]


def test_chat_endpoint_refuses_full_solution_requests(client):
    response = client.post(
        "/v1/chat/respond",
        json={
            "user_id": "demo-user",
            "message": "Реши полностью задачу 27 и дай готовый код",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["mode"] == "refuse_full_solution"
    assert payload["data"]["refusal"] is True


def test_code_check_returns_syntax_feedback(client):
    response = client.post(
        "/v1/code/check",
        json={
            "user_id": "demo-user",
            "language": "python",
            "code": "for i in range(3)\n    print(i)",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["accepted"] is False
    assert payload["data"]["issues"][0]["code"] == "syntax_error"
    assert payload["data"]["summary"]["syntax_ok"] is False


def test_code_check_blocks_unsafe_patterns(client):
    response = client.post(
        "/v1/code/check",
        json={
            "user_id": "demo-user",
            "language": "python",
            "code": "import os\nprint('hi')",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["accepted"] is False
    assert payload["data"]["summary"]["execution_status"] == "blocked"


def test_chat_endpoint_persists_session_history_and_hint_level(db_client, db_manager):
    first_response = db_client.post(
        "/v1/chat/respond",
        json={
            "user_id": "db-user",
            "message": "Помоги с задачей 27 по массивам",
            "task_context": {
                "subject": "informatics",
                "topic": "task_27",
                "task_id": "27-array-scan",
            },
        },
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()
    session_id = first_payload["data"]["session_id"]
    assert first_payload["data"]["hint_level"] == 1

    second_response = db_client.post(
        "/v1/chat/respond",
        json={
            "session_id": session_id,
            "user_id": "db-user",
            "message": "Дай еще одну подсказку по этой задаче",
            "task_context": {
                "subject": "informatics",
                "topic": "task_27",
                "task_id": "27-array-scan",
            },
        },
    )

    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["data"]["hint_level"] == 2

    session_repository = ChatSessionRepository()
    message_repository = ChatMessageRepository()
    with db_manager.session_scope() as db:
        stored_session = session_repository.get_by_session_id(db, session_id)
        stored_messages = message_repository.list_for_session(db, session_id=session_id)

    assert stored_session is not None
    assert stored_session.current_hint_level == 2
    assert len(stored_messages) == 4


def test_code_check_keeps_session_history_in_database(db_client, db_manager):
    response = db_client.post(
        "/v1/code/check",
        json={
            "user_id": "db-user",
            "language": "python",
            "code": "print(sum([1, 2, 3]))",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    session_id = payload["data"]["session_id"]
    assert payload["data"]["accepted"] is True

    message_repository = ChatMessageRepository()
    with db_manager.session_scope() as db:
        stored_messages = message_repository.list_for_session(db, session_id=session_id)

    assert len(stored_messages) == 2

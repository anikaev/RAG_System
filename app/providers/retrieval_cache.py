from __future__ import annotations

import hashlib
import json
from typing import Protocol

from redis import Redis
from redis.exceptions import RedisError

from app.providers.interfaces import RetrievedContext


class RetrievalCacheBackend(Protocol):
    def get_many(self, key: str) -> list[RetrievedContext] | None:
        ...

    def set_many(
        self,
        key: str,
        values: list[RetrievedContext],
        *,
        ttl_seconds: int,
    ) -> None:
        ...

    def is_available(self) -> bool:
        ...


class NoOpRetrievalCache:
    def get_many(self, key: str) -> list[RetrievedContext] | None:
        return None

    def set_many(
        self,
        key: str,
        values: list[RetrievedContext],
        *,
        ttl_seconds: int,
    ) -> None:
        return None

    def is_available(self) -> bool:
        return False


class MemoryRetrievalCache:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get_many(self, key: str) -> list[RetrievedContext] | None:
        payload = self._store.get(key)
        if payload is None:
            return None
        return _decode_contexts(payload)

    def set_many(
        self,
        key: str,
        values: list[RetrievedContext],
        *,
        ttl_seconds: int,
    ) -> None:
        del ttl_seconds
        self._store[key] = _encode_contexts(values)

    def is_available(self) -> bool:
        return True


class RedisRetrievalCache:
    def __init__(self, redis_url: str) -> None:
        self.client = Redis.from_url(redis_url, decode_responses=True)

    def get_many(self, key: str) -> list[RetrievedContext] | None:
        try:
            payload = self.client.get(key)
        except RedisError:
            return None
        if not isinstance(payload, str):
            return None
        return _decode_contexts(payload)

    def set_many(
        self,
        key: str,
        values: list[RetrievedContext],
        *,
        ttl_seconds: int,
    ) -> None:
        try:
            self.client.set(key, _encode_contexts(values), ex=ttl_seconds)
        except RedisError:
            return None

    def is_available(self) -> bool:
        try:
            return bool(self.client.ping())
        except RedisError:
            return False


def build_retrieval_cache_key(
    namespace: str,
    query: str,
    *,
    subject: str | None = None,
    topic: str | None = None,
    task_id: str | None = None,
    top_k: int = 3,
) -> str:
    payload = json.dumps(
        {
            "query": query,
            "subject": subject,
            "topic": topic,
            "task_id": task_id,
            "top_k": top_k,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"retrieval:{namespace}:{digest}"


def _encode_contexts(values: list[RetrievedContext]) -> str:
    payload = [value.model_dump(mode="json") for value in values]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _decode_contexts(payload: str) -> list[RetrievedContext]:
    raw_values = json.loads(payload)
    if not isinstance(raw_values, list):
        return []
    return [RetrievedContext.model_validate(item) for item in raw_values]

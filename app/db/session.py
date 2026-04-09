from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base


class DatabaseSessionManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = self._create_engine(settings)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    @staticmethod
    def _create_engine(settings: Settings) -> Engine:
        connect_args: dict[str, object] = {}
        if settings.postgres_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        return create_engine(
            settings.postgres_url,
            future=True,
            pool_pre_ping=True,
            echo=settings.database_echo,
            connect_args=connect_args,
        )

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_schema(self) -> None:
        Base.metadata.create_all(bind=self.engine)

    def check_connection(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

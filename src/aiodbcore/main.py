import asyncio
import re
import types as tys
import typing as ty
from abc import ABC
from dataclasses import dataclass, field

from .core_async import AsyncDBCore
from .core_sync import SyncDBCore
from .tools import get_base_generics


@dataclass
class DBPath:
    name: str
    path: str
    sync_connection_kwargs: dict[str, ty.Any] = field(default_factory=dict)
    async_connection_kwargs: dict[str, ty.Any] = field(default_factory=dict)
    sync_inited: bool = False
    async_inited: bool = False

    @property
    def sync_name(self):
        return f"{self.name}_sync"

    @property
    def async_name(self):
        return f"{self.name}_async"


class Database[Models](ABC):
    _dbs: dict[str, DBPath] = {}
    _models: Models

    @classmethod
    def init(
        cls,
        database_path: str,
        db_name: str = "main",
        sync_connection_kwargs: dict[str, ty.Any] | None = None,
        async_connection_kwargs: dict[str, ty.Any] | None = None,
        **connection_kwargs,
    ):
        cls._models = get_base_generics(cls, Database)[Models]
        if db_name in cls._dbs:
            raise ValueError("DB with this name already initialized")
        if not (
            match := re.fullmatch(
                r"(?P<provider>.+?)(\+(?P<library>.+?))?://(?P<db>.+)",
                database_path,
            )
        ):
            raise ValueError("Invalid db path. pass it like `sqlite://db.path`")
        if match.group("library"):
            raise ValueError(
                "Specifying a library is not supported when inheriting "
                "the `Database` class."
            )

        if not sync_connection_kwargs:
            sync_connection_kwargs = {}
        sync_connection_kwargs.update(connection_kwargs)
        if not async_connection_kwargs:
            async_connection_kwargs = {}
        async_connection_kwargs.update(connection_kwargs)

        cls._dbs[db_name] = DBPath(
            db_name,
            database_path,
            sync_connection_kwargs,
            async_connection_kwargs,
        )

    def __init__(self, db_name: str = "main"):
        if not self._dbs:
            raise RuntimeError("DB is not initialized")
        if not (db := self._dbs.get(db_name)):
            raise ValueError(f"DB `{db_name}` is not initialized")
        self._db = db

    def __enter__(self) -> SyncDBCore[Models]:
        if not self._db.sync_inited:
            tys.new_class("DB", (SyncDBCore[self._models],)).init(
                self._db.path,
                self._db.sync_name,
                **self._db.sync_connection_kwargs,
            )
            self._db.sync_inited = True
        return SyncDBCore[Models](self._db.sync_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self) -> AsyncDBCore[Models]:
        if not self._db.async_inited:
            tys.new_class("DB", (AsyncDBCore[self._models],)).init(
                self._db.path,
                self._db.async_name,
                **self._db.async_connection_kwargs,
            )
            self._db.async_inited = True
        return AsyncDBCore[Models](self._db.async_name)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    def close_connections(cls):
        sync_inited = async_inited = False
        for db in cls._dbs.values():
            if db.sync_inited:
                sync_inited = True
            if db.async_inited:
                async_inited = True
        if sync_inited:
            SyncDBCore.close_connections()
        if async_inited:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(AsyncDBCore.close_connections())
            except RuntimeError:
                asyncio.run(AsyncDBCore.close_connections())

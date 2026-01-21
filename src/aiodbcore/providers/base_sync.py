from __future__ import annotations

import threading
import typing as ty
from abc import ABC, abstractmethod

from ..exceptions import ConnectionIsNotAccrued
from .base import (
    BaseConnectionWrapper,
    BasePoolConnectionWrapper,
    BaseProvider,
    translate_exceptions,
)

if ty.TYPE_CHECKING:
    from .base import InsertQuery, Query, SelectQuery


class BaseSyncProvider[ConnType](BaseProvider[ConnType], ABC):
    """
    Base class for sync SQL providers.
    ConnType : type of connection instance.
    """

    @abstractmethod
    def ensure_connection(
        self,
    ) -> SyncConnectionWrapper[ConnType] | SyncPoolConnectionWrapper[ConnType]:
        raise NotImplementedError()

    @abstractmethod
    def _fetchone(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> tuple[ty.Any, ...] | None:
        raise NotImplementedError()

    @abstractmethod
    def _fetchall(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> list[tuple[ty.Any, ...]]:
        raise NotImplementedError()

    @translate_exceptions
    def execute(self, query: Query, args: ty.Sequence[ty.Any] = ()):
        args = tuple(self.adapt_value(arg) for arg in args)
        return self._execute(query, args)

    @translate_exceptions
    def execute_insert_query(
        self, query: InsertQuery, args: ty.Sequence[ty.Any]
    ) -> list[int]:
        args = tuple(self.adapt_value(arg) for arg in args)
        return [row[0] for row in self._fetchall(query, args)]

    @translate_exceptions
    def fetchone(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> tuple[ty.Any, ...] | None:
        args = tuple(self.adapt_value(arg) for arg in args)
        return self._fetchone(query, args)

    @translate_exceptions
    def fetchall(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> list[tuple[ty.Any, ...]]:
        args = tuple(self.adapt_value(arg) for arg in args)
        print(query)
        return self._fetchall(query, args)


class SyncConnectionWrapper[ConnType](BaseConnectionWrapper[ConnType]):
    def __init__(self, provider: BaseProvider[ConnType], lock: threading.Lock):
        self.provider = provider
        self.connection: ConnType | None = None
        self._lock = lock

    def ensure_connection(self) -> None:
        if not self.connection:
            self.provider.create_connection()
            self.connection = self.provider.connection

    def __enter__(self) -> ConnType:
        self._lock.acquire()
        self.ensure_connection()
        if self.connection is None:
            raise ConnectionIsNotAccrued()
        return self.connection

    def __exit__(self, *_):
        self._lock.release()


class SyncPoolConnectionWrapper[ConnType](BasePoolConnectionWrapper[ConnType]):
    def __init__(
        self, provider: BaseProvider[ConnType], pool_init_lock: threading.Lock
    ):
        self.provider = provider
        self.connection: ConnType | None = None
        self._pool_init_lock = pool_init_lock

    def ensure_connection(self) -> None:
        if not self.provider.connections_pool:
            with self._pool_init_lock:
                if not self.provider.connections_pool:
                    self.provider.create_connection()

    def __enter__(self) -> ConnType:
        self.ensure_connection()
        self.connection = self.provider.connections_pool.acquire()
        if self.connection is None:
            raise ConnectionIsNotAccrued()
        return self.connection

    def __exit__(self, *_):
        self.provider.connections_pool.release(self.connection)

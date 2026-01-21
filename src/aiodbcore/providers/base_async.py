from __future__ import annotations

import asyncio
import typing as ty
from abc import ABC, abstractmethod
from functools import wraps

from ..exceptions import ConnectionIsNotAccrued
from .base import BaseConnectionWrapper, BasePoolConnectionWrapper, BaseProvider

if ty.TYPE_CHECKING:
    from .base import InsertQuery, Query, SelectQuery


def translate_exceptions(func):
    @wraps(func)
    async def _wrapper(self: BaseAsyncProvider, query, args=()):
        try:
            return await func(self, query, args)
        except Exception as e:
            raise self._translate_exception(e, query, args)

    return _wrapper


class BaseAsyncProvider[ConnType](BaseProvider[ConnType], ABC):
    """
    Base class for async SQL providers.
    ConnType : type of connection instance.
    """

    @abstractmethod
    def ensure_connection(
        self,
    ) -> (
        AsyncConnectionWrapper[ConnType] | AsyncPoolConnectionWrapper[ConnType]
    ):
        raise NotImplementedError()

    @abstractmethod
    async def _fetchone(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> tuple[ty.Any, ...] | None:
        raise NotImplementedError()

    @abstractmethod
    async def _fetchall(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> list[tuple[ty.Any, ...]]:
        raise NotImplementedError()

    @translate_exceptions
    async def execute(self, query: Query, args: ty.Sequence[ty.Any] = ()):
        args = tuple(self.adapt_value(arg) for arg in args)
        return await self._execute(query, args)

    @translate_exceptions
    async def execute_insert_query(
        self, query: InsertQuery, args: ty.Sequence[ty.Any]
    ) -> list[int]:
        args = tuple(self.adapt_value(arg) for arg in args)
        return [row[0] for row in await self._fetchall(query, args)]

    @translate_exceptions
    async def fetchone(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> tuple[ty.Any, ...] | None:
        args = tuple(self.adapt_value(arg) for arg in args)
        return await self._fetchone(query, args)

    @translate_exceptions
    async def fetchall(
        self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()
    ) -> list[tuple[ty.Any, ...]]:
        args = tuple(self.adapt_value(arg) for arg in args)
        return await self._fetchall(query, args)


class AsyncConnectionWrapper[ConnType](BaseConnectionWrapper[ConnType]):
    def __init__(self, provider: BaseProvider[ConnType], lock: asyncio.Lock):
        self.provider = provider
        self.connection: ConnType | None = None
        self._lock = lock

    async def ensure_connection(self) -> None:
        if not self.connection:
            await self.provider.create_connection()
            self.connection = self.provider.connection

    async def __aenter__(self) -> ConnType:
        await self._lock.acquire()
        await self.ensure_connection()
        if self.connection is None:
            raise ConnectionIsNotAccrued()
        return self.connection

    async def __aexit__(self, *_):
        self._lock.release()


class AsyncPoolConnectionWrapper[ConnType](BasePoolConnectionWrapper[ConnType]):
    def __init__(
        self, provider: BaseProvider[ConnType], pool_init_lock: asyncio.Lock
    ):
        self.provider = provider
        self.connection: ConnType | None = None
        self._pool_init_lock = pool_init_lock

    async def ensure_connection(self) -> None:
        if not self.provider.connections_pool:
            async with self._pool_init_lock:
                if not self.provider.connections_pool:
                    await self.provider.create_connection()

    async def __aenter__(self) -> ConnType:
        await self.ensure_connection()
        self.connection = await self.provider.connections_pool.acquire()
        if self.connection is None:
            raise ConnectionIsNotAccrued()
        return self.connection

    async def __aexit__(self, *_):
        await self.provider.connections_pool.release(self.connection)

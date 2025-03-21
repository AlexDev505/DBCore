from __future__ import annotations

import asyncio
import dataclasses
import string
import typing as ty
from abc import ABC, abstractmethod
from contextlib import suppress
from datetime import datetime, date, time
from enum import Enum
from functools import wraps

import orjson

from aiodbcore.exceptions import DBError


def translate_exceptions(func):
    @wraps(func)
    async def _wrapper(self: BaseProvider, query, args=()):
        try:
            return await func(self, query, args)
        except Exception as e:
            raise self._translate_exception(e, query, args)

    return _wrapper


class BaseProvider[ConnType](ABC):
    """
    Base class for SQL providers.
    T : type of connection instance.
    """

    TYPING_MAP = {"str": "TEXT", "int": "INTEGER", "float": "REAL"}
    """ comparison of data types in python and SQL """

    DEFAULT_FIELD_TYPE = "BLOB"
    """
    default data type. 
    will be used if the type of field is not defined in `TYPING_MAP` 
    """

    PLACEHOLDER: ty.Callable[[int], str] = staticmethod(lambda _: "?")
    """
    indexed arguments placeholder.
    ty.Callable[[<arg_index>], <placeholder>]
    """

    """ SQL queries templates """
    CREATE_TABLE_QUERY_TEMPLATE = (
        'CREATE TABLE IF NOT EXISTS "{table_name}" '
        "(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, {fields})"
    )
    INSERT_INTO_QUERY_TEMPLATE = (
        'INSERT INTO "{table_name}" ({fields}) VALUES ({values})'
    )
    SELECT_QUERY_TEMPLATE = (
        'SELECT * FROM "{table_name}"{where}{order_by}{desc}{limit}{offset}'
    )
    UPDATE_QUERY_TEMPLATE = 'UPDATE "{table_name}" SET {fields}{where}'
    DELETE_FROM_QUERY_TEMPLATE = 'DELETE FROM "{table_name}"{where}'
    DROP_TABLE_QUERY_TEMPLATE = 'DROP TABLE "{table_name}"'

    CREATE_TABLE_FIELD_TEMPLATE = "{field_name} {type}{unique}"
    UNIQUE_FIELD = "UNIQUE"

    connections_pool: ty.Any
    connection: ConnType | None

    def __init__(self, db_path: str, **connection_kwargs):
        """
        :param db_path: path to db.
        :param connection_kwargs: params of db connection
        """
        self.db_path = self.modify_db_path(db_path)
        self.connection_kwargs = connection_kwargs

    @abstractmethod
    async def create_connection(self) -> None:
        """
        Connects to db.
        """
        raise NotImplementedError()

    @abstractmethod
    async def close_connection(self) -> None:
        """
        Closes db connection.
        """
        raise NotImplementedError()

    @abstractmethod
    def ensure_connection(
        self,
    ) -> ConnectionWrapper[ConnType] | PoolConnectionWrapper[ConnType]:
        """
        Acquires a connection from the pool.
        """
        raise NotImplementedError()

    @translate_exceptions
    async def execute(self, query: str, args: ty.Sequence[ty.Any] = ()):
        """
        Executes SQL query.
        :param query: SQL statement.
        :param args: statement params.
        :returns: cursor instance.
        """
        args = tuple(self.adapt_value(arg) for arg in args)
        return await self._execute(query, args)

    @abstractmethod
    async def _execute(self, query: str, args: ty.Sequence[ty.Any] = ()):
        raise NotImplementedError()

    def prepare_create_table_query(
        self, table_name: str, fields: dict[str, tuple[ty.Any, bool]]
    ) -> str:
        fields = (
            self.CREATE_TABLE_FIELD_TEMPLATE.format(
                field_name=field_name,
                type=self._get_sql_type(field_type),
                unique=f" {self.UNIQUE_FIELD}" if unique else "",
            )
            for field_name, (field_type, unique) in fields.items()
            if field_name != "id"
        )
        return self.CREATE_TABLE_QUERY_TEMPLATE.format(
            table_name=table_name.lower(), fields=", ".join(fields)
        )

    def prepare_insert_query(
        self, table_name: str, field_names: ty.Sequence[str]
    ) -> str:
        return self.INSERT_INTO_QUERY_TEMPLATE.format(
            table_name=table_name.lower(),
            fields=", ".join(field_names),
            values=", ".join(
                self.PLACEHOLDER(i) for i in range(1, len(field_names) + 1)
            ),
        )

    @translate_exceptions
    async def execute_insert_query(self, query: str, args: ty.Sequence[ty.Any]) -> int:
        """
        Executes SQL insert query.
        :param query: SQL statement.
        :param args: statement params.
        :returns: ID of the inserted row.
        """
        args = tuple(self.adapt_value(arg) for arg in args)
        return await self._execute_insert_query(query, args)

    @abstractmethod
    async def _execute_insert_query(
        self, query: str, values: ty.Sequence[ty.Any]
    ) -> int:
        raise NotImplementedError()

    def prepare_select_query(
        self,
        table_name: str,
        where: str | None = None,
        order_by: str | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> str:
        return self.SELECT_QUERY_TEMPLATE.format(
            table_name=table_name.lower(),
            where=(
                f" WHERE {self._paste_placeholders(where)}" if where is not None else ""
            ),
            order_by=f" ORDER BY {order_by}" if order_by is not None else "",
            desc=f" DESC" if reverse else "",
            limit=f" LIMIT {limit}" if limit is not None else "",
            offset=f" OFFSET {offset}" if offset else "",
        )

    @translate_exceptions
    async def fetchone(
        self, query: str, args: ty.Sequence[ty.Any] = ()
    ) -> tuple[ty.Any] | None:
        """
        Executes SQL select query and return one row.
        :param query: SQL statement.
        :param args: statement params.
        :returns: raw data from db.
        """
        args = tuple(self.adapt_value(arg) for arg in args)
        return await self._fetchone(query, args)

    @abstractmethod
    async def _fetchone(
        self, query: str, args: ty.Sequence[ty.Any] = ()
    ) -> tuple[ty.Any] | None:
        raise NotImplementedError()

    @translate_exceptions
    async def fetchall(
        self, query: str, args: ty.Sequence[ty.Any] = ()
    ) -> list[tuple[ty.Any]]:
        """
        Executes SQL select query and return all rows.
        :param query: SQL statement.
        :param args: statement params.
        :returns: list of raw data from db.
        """
        args = tuple(self.adapt_value(arg) for arg in args)
        return await self._fetchall(query, args)

    @abstractmethod
    async def _fetchall(
        self, query: str, args: ty.Sequence[ty.Any] = ()
    ) -> list[tuple[ty.Any]]:
        raise NotImplementedError()

    def prepare_update_query(
        self, table_name: str, field_names: ty.Sequence[str], where: str | None = None
    ) -> str:
        return self._paste_placeholders(
            self.UPDATE_QUERY_TEMPLATE.format(
                table_name=table_name.lower(),
                fields=", ".join(f"{field_name}={{}}" for field_name in field_names),
                where=(f" WHERE {where}" if where is not None else ""),
            )
        )

    def prepare_delete_query(self, table_name: str, where: str | None = None) -> str:
        return self.DELETE_FROM_QUERY_TEMPLATE.format(
            table_name=table_name.lower(),
            where=(
                f" WHERE {self._paste_placeholders(where)}" if where is not None else ""
            ),
        )

    def prepare_drop_table_query(self, table_name: str) -> str:
        return self.DROP_TABLE_QUERY_TEMPLATE.format(table_name=table_name.lower())

    def _get_sql_type(self, field_type: ty.Any) -> str:
        """
        :param field_type: Python data type.
        :return: SQL data type from `TYPING_MAP` or `DEFAULT_FIELD_TYPE`.
        """
        return self.TYPING_MAP.get(field_type.__name__, self.DEFAULT_FIELD_TYPE)

    def _paste_placeholders(self, query: str) -> str:
        placeholders_count = len(
            [x[1] for x in string.Formatter().parse(query) if x[1] is not None]
        )
        return query.format(
            *(self.PLACEHOLDER(i) for i in range(1, placeholders_count + 1))
        )

    def adapt_value(self, obj: ty.Any) -> ty.Any:
        """
        Adapts `obj` to suitable for db type.
        """
        if type(obj).__name__ in self.TYPING_MAP:
            return obj
        elif isinstance(obj, Enum):
            obj = obj.value
        elif isinstance(obj, (datetime, date, time)):
            obj = obj.isoformat()
        elif hasattr(obj, "to_dump"):
            obj = obj.to_dump()
        elif dataclasses.is_dataclass(obj):
            obj = dataclasses.asdict(obj)
        elif isinstance(obj, dict) and type(obj) is not dict:
            obj = dict(obj)
        elif isinstance(obj, list) and type(obj) is not list:
            obj = list(obj)
        return self._default_adapt_value(obj)

    @staticmethod
    def _default_adapt_value(obj: ty.Any) -> ty.Any:
        """
        Adapts `obj` to suitable type for `DEFAULT_FIELD_TYPE`.
        """
        return orjson.dumps(obj)

    def convert_value(self, obj: ty.Any, python_type: ty.Type) -> ty.Any:
        """
        Wraps raw data form db to suitable type for model.
        """
        if type(obj) is python_type:
            return obj
        if str(type(obj).__name__) in self.TYPING_MAP:
            return python_type(obj)

        obj = self._default_convert_value(obj)
        with suppress(ValueError, TypeError):
            if python_type in {datetime, date, time}:
                return datetime.fromisoformat(obj)
            if dataclasses.is_dataclass(python_type):
                if type(obj) is dict:
                    return python_type(**obj)
                return python_type(*obj)
            return python_type(obj)

    @staticmethod
    def _default_convert_value(obj: ty.Any) -> ty.Any:
        """
        Converts raw data from db `DEFAULT_FIELD_TYPE` to python data type.
        :param obj:
        :return:
        """
        return orjson.loads(obj)

    @staticmethod
    def modify_db_path(db_path: str) -> str:
        """
        Brings the url to the desired format.
        """
        return db_path

    def _translate_exception(
        self, exception: Exception, query: str, args: ty.Sequence[ty.Any]
    ) -> DBError:
        return DBError(query, args, exception)


class ConnectionWrapper[ConnType]:
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
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()


class PoolConnectionWrapper[ConnType]:
    def __init__(self, provider: BaseProvider[ConnType], pool_init_lock: asyncio.Lock):
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
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.provider.connections_pool.release(self.connection)

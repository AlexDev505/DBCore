from __future__ import annotations

import dataclasses
import string
import typing as ty
from abc import ABC, abstractmethod
from contextlib import suppress
from datetime import date, datetime, time
from enum import Enum
from functools import wraps
from inspect import isclass

import orjson

from ..exceptions import QueryError
from ..tools import Construct, convert_type

type Query = str
type CreateTableQuery = Query
type InsertQuery = Query
type SelectQuery = Query
type UpdateQuery = Query
type DeleteQuery = Query
type DropTableQuery = Query


def translate_exceptions(func):
    @wraps(func)
    def _wrapper(self: BaseProvider, query, args=()):
        try:
            return func(self, query, args)
        except Exception as e:
            raise self._translate_exception(e, query, args)

    return _wrapper


class BaseProvider[ConnType](ABC):
    """
    Base class for SQL providers.
    ConnType : type of connection instance.
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
    CREATE_TABLE_QUERY_TEMPLATE: CreateTableQuery = (
        'CREATE TABLE IF NOT EXISTS "{table_name}" '
        "(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, {fields})"
    )
    INSERT_INTO_QUERY_TEMPLATE: InsertQuery = (
        'INSERT INTO "{table_name}" ({fields}) VALUES {rows}  RETURNING id'
    )
    SELECT_QUERY_TEMPLATE: SelectQuery = 'SELECT {fields} FROM "{table_name}"{join}{where}{order_by}{limit}{offset}'
    UPDATE_QUERY_TEMPLATE: UpdateQuery = (
        'UPDATE "{table_name}" SET {fields}{where}'
    )
    DELETE_FROM_QUERY_TEMPLATE: DeleteQuery = (
        'DELETE FROM "{table_name}"{where}'
    )
    DROP_TABLE_QUERY_TEMPLATE: DropTableQuery = 'DROP TABLE "{table_name}"'

    RETURNING_TEMPLATE = "RETURNING {fields}"
    CREATE_TABLE_FIELD_TEMPLATE = "{field_name} {type}{unique}"
    UNIQUE_FIELD = "UNIQUE"
    CREATE_INDEX_TEMPLATE = (
        'CREATE {unique}INDEX IF NOT EXISTS {name} ON "{table_name}"({fields})'
    )

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
    def create_connection(self):
        """
        Connects to db.
        """
        raise NotImplementedError()

    @abstractmethod
    def close_connection(self):
        """
        Closes db connection.
        """
        raise NotImplementedError()

    @abstractmethod
    def ensure_connection(
        self,
    ) -> BaseConnectionWrapper[ConnType] | BasePoolConnectionWrapper[ConnType]:
        """
        Acquires a connection from the pool.
        """
        raise NotImplementedError()

    @abstractmethod
    @translate_exceptions
    def execute(self, query: Query, args: ty.Sequence[ty.Any] = ()):
        """
        Executes SQL query.
        :param query: SQL statement.
        :param args: statement params.
        :returns: cursor instance.
        """
        raise NotImplementedError()

    @abstractmethod
    def _execute(self, query: Query, args: ty.Sequence[ty.Any] = ()) -> ty.Any:
        raise NotImplementedError()

    @abstractmethod
    def executescript(self, query: Query) -> ty.Any:
        raise NotImplementedError()

    def prepare_create_table_query(
        self,
        table_name: str,
        fields: dict[str, tuple[ty.Any, bool, str | None]],
    ) -> CreateTableQuery:
        query_fields = (
            self.CREATE_TABLE_FIELD_TEMPLATE.format(
                field_name=field_name,
                type=sql_type or self._get_sql_type(field_type),
                unique=f" {self.UNIQUE_FIELD}" if unique else "",
            )
            for field_name, (field_type, unique, sql_type) in fields.items()
            if field_name != "id"
        )
        return self.CREATE_TABLE_QUERY_TEMPLATE.format(
            table_name=table_name, fields=", ".join(query_fields)
        )

    def prepare_create_index_query(
        self,
        table_name: str,
        index_name: str,
        field_names: ty.Sequence[str],
        unique: bool = False,
    ) -> str:
        return self.CREATE_INDEX_TEMPLATE.format(
            unique="UNIQUE " if unique else "",
            name=index_name,
            table_name=table_name,
            fields=", ".join(field_names),
        )

    def prepare_insert_query(
        self, table_name: str, field_names: ty.Sequence[str], rows: int
    ) -> InsertQuery:
        return self.INSERT_INTO_QUERY_TEMPLATE.format(
            table_name=table_name,
            fields=", ".join(field_names),
            rows=", ".join(
                [
                    "("
                    + ", ".join(
                        self.PLACEHOLDER(i)
                        for i in range(
                            1 + pad * len(field_names),
                            len(field_names) + 1 + pad * len(field_names),
                        )
                    )
                    + ")"
                    for pad in range(rows)
                ]
            ),
        )

    @abstractmethod
    @translate_exceptions
    def execute_insert_query(
        self, query: InsertQuery, args: ty.Sequence[ty.Any]
    ):
        """
        Executes SQL insert query.
        :param query: SQL statement.
        :param args: statement params.
        :returns: ID of the inserted row.
        """
        raise NotImplementedError()

    def prepare_select_query(
        self,
        table_name: str,
        fields: tuple[str, ...] | None = None,
        join: str | None = None,
        where: str | None = None,
        order_by: tuple[str | tuple[str, bool], ...] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> SelectQuery:
        return self.SELECT_QUERY_TEMPLATE.format(
            table_name=table_name,
            fields=", ".join(fields) if fields else "*",
            join=f" {join}" if join else "",
            where=(
                f" WHERE {self._paste_placeholders(where)}"
                if where is not None
                else ""
            ),
            order_by=(
                (
                    " ORDER BY "
                    + ", ".join(
                        f"{field} {'DESC' if reverse else ''}"
                        for field, reverse in map(
                            lambda x: x if isinstance(x, tuple) else (x, False),
                            order_by,
                        )
                    )
                )
                if order_by is not None
                else ""
            ),
            limit=f" LIMIT {limit}" if limit is not None else "",
            offset=f" OFFSET {offset}" if offset else "",
        )

    @abstractmethod
    def fetchone(self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()):
        """
        Executes SQL select query and return one row.
        :param query: SQL statement.
        :param args: statement params.
        :returns: raw data from db.
        """
        raise NotImplementedError()

    @abstractmethod
    def _fetchone(self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()):
        raise NotImplementedError()

    @abstractmethod
    @translate_exceptions
    def fetchall(self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()):
        """
        Executes SQL select query and return all rows.
        :param query: SQL statement.
        :param args: statement params.
        :returns: list of raw data from db.
        """
        raise NotImplementedError()

    @abstractmethod
    def _fetchall(self, query: SelectQuery, args: ty.Sequence[ty.Any] = ()):
        raise NotImplementedError()

    def prepare_update_query(
        self,
        table_name: str,
        fields: dict[str, str],  # {field_name: math_operator or '=', ...}
        where: str | None = None,
    ) -> UpdateQuery:
        return self._paste_placeholders(
            self.UPDATE_QUERY_TEMPLATE.format(
                table_name=table_name,
                fields=", ".join(
                    f"{
                        f'{field_name}='
                        if op == '='
                        else f'{field_name}={field_name}{op}'
                    }{{}}"
                    for field_name, op in fields.items()
                ),
                where=(f" WHERE {where}" if where is not None else ""),
            )
        )

    def prepare_delete_query(
        self, table_name: str, where: str | None = None
    ) -> DeleteQuery:
        return self.DELETE_FROM_QUERY_TEMPLATE.format(
            table_name=table_name,
            where=(
                f" WHERE {self._paste_placeholders(where)}"
                if where is not None
                else ""
            ),
        )

    def prepare_drop_table_query(self, table_name: str) -> DropTableQuery:
        return self.DROP_TABLE_QUERY_TEMPLATE.format(table_name=table_name)

    def _get_sql_type(self, field_type: ty.Any) -> str:
        """
        :param field_type: Python data type.
        :return: SQL data type from `TYPING_MAP` or `DEFAULT_FIELD_TYPE`.
        """
        return self.TYPING_MAP.get(
            (
                field_type if isclass(field_type) else field_type.__class__
            ).__name__,
            self.DEFAULT_FIELD_TYPE,
        )

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
            if isclass(obj):
                raise TypeError("Cannot adapt dataclass class")
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

    def convert_value[T](
        self, obj: ty.Any, python_type: Construct[T]
    ) -> T | None:
        """
        Wraps raw data form db to suitable type for model.
        """
        if type(obj) is python_type:
            return obj
        if str(type(obj).__name__) in self.TYPING_MAP:
            return python_type(obj)

        obj = self._default_convert_value(obj)
        with suppress(ValueError, TypeError):
            return convert_type(obj, python_type)

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
        self, exception: Exception, query: str, params: ty.Sequence[ty.Any]
    ) -> QueryError:
        return QueryError(query, params, exception)


class BaseConnectionWrapper[ConnType](ABC):
    def __init__(self, provider: BaseProvider[ConnType], lock):
        raise NotImplementedError()


class BasePoolConnectionWrapper[ConnType](ABC):
    def __init__(self, provider: BaseProvider[ConnType], pool_init_lock):
        raise NotImplementedError()

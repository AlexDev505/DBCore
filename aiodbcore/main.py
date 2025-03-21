from __future__ import annotations

import types as tys
import typing as ty

from .models import ModelField
from .models import ModelSignature, prepare_model
from .providers import get_provider
from .tools import get_changed_attributes


if ty.TYPE_CHECKING:
    from .operators import Operator
    from .providers import BaseProvider


class AsyncDBCore[Models]:
    """
    Main db class.
    You can implement your needs to the database in the classroom class
    or use this class directly.
    """

    signatures: dict[str, ModelSignature] = {}
    dbs: dict[str, BaseProvider] = {}
    db_names: dict[str, str] = {}

    @classmethod
    def init(
        cls, database_path: str, db_name: str = "main", **connection_kwargs
    ) -> None:
        """
        Initialize the db.
        :param database_path: path to db.
        :param db_name: Connection name is used for multi connection.
        :param connection_kwargs: params for connection provider.
        """
        if database_path is cls.db_names:
            raise RuntimeError("This DB already initialized")
        if db_name in cls.db_names.values():
            raise ValueError("DB with this name already initialized")

        generic_types = ty.get_args(cls.__orig_bases__[0])[0]  # noqa
        if type(generic_types) is ty.TypeVar:
            raise NotImplementedError("")
        elif type(generic_types) in {ty.Union, tys.UnionType}:
            models = ty.get_args(generic_types)
        else:
            models = [generic_types]

        if not cls.signatures:
            cls.signatures = {model.__name__: prepare_model(model) for model in models}

        cls.dbs[db_name] = get_provider(database_path)(
            database_path, **connection_kwargs
        )

    @classmethod
    async def close_connections(cls) -> None:
        """
        Closes all connections.
        """
        for provider in cls.dbs.values():
            await provider.close_connection()

    def __init__(self, db: str = "main"):
        if not self.dbs:
            raise RuntimeError("DB is not initialized")
        self.provider = self.dbs.get(db)
        if not self.provider:
            raise ValueError(f"DB `{db}` is not initialized")

    async def execute(self, query: str, args: ty.Sequence[ty.Any] = ()):
        """
        Executes SQL query.
        :param query: SQL statement.
        :param args: statement params.
        :returns: cursor instance.
        """
        return await self.provider.execute(query, args)

    async def create_tables(self) -> None:
        """
        Creates all tables.
        """
        for model_name, signature in self.signatures.items():
            query = self.provider.prepare_create_table_query(
                model_name,
                {
                    field.name: (field.python_type, field.unique)
                    for field in signature.fields
                },
            )
            await self.provider.execute(query)

    async def insert(self, obj: Models) -> Models:
        """
        Inserts obj to bd.
        :param obj: obj to insert.
        :returns: The same object, but with an identifier in the database.
        """
        signature = self.signatures[obj.__class__.__name__]
        field_names = []
        values = []
        for field in signature.fields:
            if field.name != "id":
                field_names.append(field.name)
                values.append(getattr(obj, field.name))
        query = self.provider.prepare_insert_query(signature.name, field_names)
        obj_id = await self.provider.execute_insert_query(query, values)
        obj.id = obj_id
        return obj

    def _prepare_select_query(
        self,
        model_name: str,
        where: Operator | None = None,
        order_by: ModelField | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> str:
        return self.provider.prepare_select_query(
            model_name,
            where=str(where) if where is not None else None,
            order_by=order_by.field.name if order_by is not None else None,
            reverse=reverse,
            limit=limit,
            offset=offset,
        )

    def _convert_data(self, model: ty.Type[Models], data: tuple[ty.Any]) -> Models:
        """
        Converts raw data from db to model.
        """
        signature = self.signatures[model.__name__]
        if len(data) != len(signature.fields):
            raise ValueError(
                f"Model {signature.name} have {len(signature.fields)} fields, "
                f"but {len(data)} given"
            )

        kwargs = {}
        for field, value in zip(signature.fields, data):
            kwargs[field.name] = self.provider.convert_value(value, field.python_type)

        return model(**kwargs)

    async def fetchone(
        self,
        model: ty.Type[Models],
        *,
        where: Operator | None = None,
        order_by: ModelField | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> Models | None:
        """
        Fetches one row from db.
        :param model: model to fetch.
        :param where: filtering statement.
        :param order_by: field for sorting.
        :param reverse: True - fetching from end of table.
        :param limit: count of rows to fetch.
        :param offset: offset of rows to fetch.
        :returns: one model or None.
        """
        query = self._prepare_select_query(
            model.__name__, where, order_by, reverse, limit, offset
        )
        if data := await self.provider.fetchone(
            query, where.get_values() if where is not None else ()
        ):
            return self._convert_data(model, data)

    async def fetchall(
        self,
        model: ty.Type[Models],
        *,
        where: Operator | None = None,
        order_by: ModelField | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Models]:
        """
        Fetches all rows from db.
        :param model: model to fetch.
        :param where: filtering statement.
        :param order_by: field for sorting.
        :param reverse: True - fetching from end of table.
        :param limit: count of rows to fetch.
        :param offset: offset of rows to fetch.
        :returns: list of model or empty list.
        """
        query = self._prepare_select_query(
            model.__name__, where, order_by, reverse, limit, offset
        )
        data = await self.provider.fetchall(
            query, where.get_values() if where is not None else ()
        )
        return [self._convert_data(model, obj) for obj in data] if data else []

    async def save(self, obj: Models) -> None:
        """
        Saves obj to db.
        :param obj: obj to save.
        """
        if not (changed_field_names := get_changed_attributes(obj)):
            return
        model = obj.__class__
        return await self.update(
            model,
            {
                getattr(model, field_name): getattr(obj, field_name)
                for field_name in changed_field_names
                if field_name != "id"
            },
            where=model.id == obj.id,
        )

    async def update(
        self,
        model: ty.Type[Models],
        fields: dict[ty.Any, ty.Any],
        *,
        where: Operator | None = None,
    ) -> None:
        """
        Executes update query.
        :param model: model to update.
        :param fields: fields to set.
        :param where: filtering statement.
        """
        query = self.provider.prepare_update_query(
            model.__name__,
            tuple(field.field.name for field in fields),
            where=str(where) if where is not None else None,
        )
        await self.execute(
            query,
            (
                *(value for value in fields.values()),
                *(where.get_values() if where is not None else ()),
            ),
        )

    async def delete(self, model: ty.Type[Models], *, where: Operator | None) -> None:
        """
        Deletes row from db.
        :param model: model from which to delete.
        :param where: filtering statement.
        """
        query = self.provider.prepare_delete_query(
            model.__name__, where=str(where) if where is not None else None
        )
        await self.execute(query, where.get_values() if where is not None else ())

    async def drop_table(self, model: ty.Type[Models]) -> None:
        """
        Drops table from db.
        :param model: model to drop.
        """
        query = self.provider.prepare_drop_table_query(model.__name__)
        await self.execute(query)

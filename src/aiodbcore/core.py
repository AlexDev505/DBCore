from __future__ import annotations

import types as tys
import typing as ty
from abc import ABC, abstractmethod

from .models import Field, prepare_model
from .operators import MathOperator
from .providers import get_provider
from .tools import get_base_generics, get_changed_attributes

if ty.TYPE_CHECKING:
    from .joins import InnerJoin, Join, LeftJoin, RightJoin
    from .models import ModelSignature
    from .operators import InvertedField, Operator
    from .providers import BaseProvider


class BaseDBCore[ProviderT: BaseProvider, Models](ABC):
    """
    Main db class.
    You can implement your queries to the database in the child class
    or use this class directly.
    """

    _use_async: bool

    signatures: dict[str, ModelSignature] = {}
    dbs: dict[str, ProviderT] = {}  # {db_name: provider}
    db_names: dict[str, str] = {}  # {db_name: db_path}

    @classmethod
    def init(
        cls, database_path: str, db_name: str = "main", **connection_kwargs
    ) -> None:
        """
        Initialize the db.
        :param database_path: Path to db.
        :param db_name: Connection name is used for multi connection.
        :param connection_kwargs: Params for connection provider.
        """
        if db_name in cls.db_names:
            raise ValueError("DB with this name already initialized")
        cls.db_names[db_name] = database_path

        generics = get_base_generics(cls, BaseDBCore)
        provider = get_provider(database_path, use_async=cls._use_async)
        if not issubclass(provider, generics[ProviderT]):
            raise TypeError(
                f"Provider {provider.__name__} is not a subclass "
                f"of {generics[ProviderT].__name__}"
            )

        if (models := generics[Models]) is ty.TypeVar:
            raise TypeError("Models is not specified")
        elif type(models) in {ty.Union, tys.UnionType}:
            models = ty.get_args(models)
        else:
            models = [models]
        cls.signatures.update(
            {
                model.__name__: prepare_model(model)
                for model in models
                if model.__name__ not in cls.signatures
            }
        )

        if database_path not in cls.dbs:
            cls.dbs[db_name] = ty.cast(
                ProviderT, provider(database_path, **connection_kwargs)
            )

    def __init__(self, db: str = "main"):
        if not self.dbs:
            raise RuntimeError("DB is not initialized")
        if not (provider := self.dbs.get(db)):
            raise ValueError(f"DB `{db}` is not initialized")
        self.provider: ProviderT = provider

    @classmethod
    @abstractmethod
    def close_connections(cls):
        """
        Closes all connections.
        """
        raise NotImplementedError()

    @abstractmethod
    def execute(self, query: str, args: ty.Sequence[ty.Any] = ()):
        """
        Executes SQL query.
        :param query: SQL statement.
        :param args: statement params.
        :returns: cursor instance.
        """
        raise NotImplementedError()

    @abstractmethod
    def create_tables(self):
        """
        Creates all tables.
        """
        raise NotImplementedError()

    @abstractmethod
    def insert(self, objs: Models | list[Models], /):
        """
        Inserts obj to bd.
        :param objs: objs to insert.
        :returns: The same object, but with an identifier in the database.
        """
        raise NotImplementedError()

    @abstractmethod
    def fetchone(
        self,
        model: ty.Type[Models],
        *,
        join: Join[Models] | None = None,
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        limit: int | None = None,
        offset: int = 0,
    ):
        """
        Fetches one row from db.
        :param model: model to fetch.
        :param join: join statement.
        :param where: filtering statement.
        :param order_by: field for sorting.
        :param limit: count of rows to fetch.
        :param offset: offset of rows to fetch.
        :returns: one model or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def fetchall(
        self,
        model: ty.Type[Models],
        *,
        join: Join[Models] | None = None,
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        limit: int | None = None,
        offset: int = 0,
    ):
        """
        Fetches all rows from db.
        :param model: model to fetch.
        :param join: join statement.
        :param where: filtering statement.
        :param order_by: field for sorting..
        :param limit: count of rows to fetch.
        :param offset: offset of rows to fetch.
        :returns: list of model or empty list.
        """
        raise NotImplementedError()

    @abstractmethod
    def save(self, obj: Models, /):
        """
        Saves obj to db.
        :param obj: obj to save.
        """
        raise NotImplementedError()

    @abstractmethod
    def update[T](
        self,
        model: ty.Type[Models],
        fields: dict[Field[T], T | MathOperator[T]],
        *,
        where: Operator | None = None,
    ):
        """
        Executes update query.
        :param model: model to update.
        :param fields: fields to set.
        :param where: filtering statement.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, model: ty.Type[Models], *, where: Operator | None):
        """
        Deletes row from db.
        :param model: model from which to delete.
        :param where: filtering statement.
        """
        raise NotImplementedError()

    @abstractmethod
    def drop_table(self, model: ty.Type[Models], /):
        """
        Drops table from db.
        :param model: model to drop.
        """
        raise NotImplementedError()

    def _prepare_create_table_query(self, signature: ModelSignature) -> str:
        create_table_query = self.provider.prepare_create_table_query(
            signature.name,
            {
                field.name: (
                    field.python_type,
                    field.unique,
                    field.sql_type,
                )
                for field in signature.fields
            },
        )

        index_queries = []
        indexes = {}
        for field in signature.fields:
            if not (index := field.index):
                continue
            if index.name not in indexes:
                indexes[index.name] = {"fields": [], "unique": False}
            indexes[index.name]["fields"].append(field.name)
            if index.unique:
                indexes[index.name]["unique"] = True
        for index_name, index_info in indexes.items():
            index_queries.append(
                self.provider.prepare_create_index_query(
                    table_name=signature.name,
                    index_name=index_name,
                    field_names=index_info["fields"],
                    unique=index_info["unique"],
                )
            )

        return ";".join((create_table_query, *index_queries))

    def _prepare_insert_query(
        self, objs: Models | list[Models]
    ) -> tuple[str, ty.Sequence[ty.Any]]:
        if not isinstance(objs, list):
            objs = [objs]
        if len(set(type(x) for x in objs)) != 1:
            raise ValueError("objects must be same types")
        signature = self.signatures[objs[0].__class__.__name__]
        field_names = [
            field.name for field in signature.fields if field.name != "id"
        ]
        values = []
        for obj in objs:
            for field in signature.fields:
                if field.name != "id":
                    values.append(getattr(obj, field.name))
        query = self.provider.prepare_insert_query(
            signature.name, field_names, len(objs)
        )
        return query, values

    def _prepare_select_query(
        self,
        model_name: str,
        fields: tuple[Field | str, ...] | None = None,
        join: Join[Models] | None = None,
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[str, ty.Sequence[ty.Any]]:
        if not fields:
            fields = (
                *self.signatures[model_name].fields,
                *(self.signatures[join.model.__name__].fields if join else ()),
            )
        if order_by and not isinstance(order_by, tuple):
            order_by = (order_by,)
        return self.provider.prepare_select_query(
            model_name,
            fields=tuple(str(x) for x in fields),
            join=str(join) if join else None,
            where=str(where) if where is not None else None,
            order_by=(
                tuple(
                    (str(x) if isinstance(x, Field) else (str(x), True))
                    for x in order_by
                )
                if order_by is not None
                else None
            ),
            limit=limit,
            offset=offset,
        ), where.get_values() if where is not None else ()

    def _prepare_update_query[T](
        self,
        model: ty.Type[Models],
        fields: dict[Field[T], T | MathOperator[T]],
        where: Operator | None = None,
    ) -> tuple[str, ty.Sequence[ty.Any]]:
        return (
            self.provider.prepare_update_query(
                model.__name__,
                {
                    field.name: value.sign
                    if isinstance(value, MathOperator)
                    else "="
                    for field, value in fields.items()
                },
                where=str(where) if where is not None else None,
            ),
            (
                *(
                    value.value if isinstance(value, MathOperator) else value
                    for value in fields.values()
                ),
                *(where.get_values() if where is not None else ()),
            ),
        )

    def _prepare_save_query(
        self, obj: Models
    ) -> tuple[str, ty.Sequence[ty.Any]] | None:
        if not (changed_field_names := get_changed_attributes(obj)):
            return
        model = obj.__class__
        return self._prepare_update_query(
            model,
            {
                getattr(model, field_name): getattr(obj, field_name)
                for field_name in changed_field_names
                if field_name != "id"
            },
            model.id == obj.id,
        )

    def _prepare_delete_query(
        self, model: ty.Type[Models], where: Operator | None
    ) -> tuple[str, ty.Sequence[ty.Any]]:
        return (
            self.provider.prepare_delete_query(
                model.__name__, where=str(where) if where is not None else None
            ),
            where.get_values() if where is not None else (),
        )

    def _prepare_drop_table_query(self, model: ty.Type[Models]) -> str:
        return self.provider.prepare_drop_table_query(model.__name__)

    @ty.overload
    def _assign_ids(self, objs: Models, obj_ids: list[int]) -> Models: ...
    @ty.overload
    def _assign_ids(
        self, objs: list[Models], obj_ids: list[int]
    ) -> list[Models]: ...
    def _assign_ids(self, objs, obj_ids):
        if not (return_list := isinstance(objs, list)):
            objs = [objs]
        for obj, obj_id in zip(objs, obj_ids):
            obj.id = obj_id
        return objs if return_list else objs[0]

    @ty.overload
    def _convert_data[Model, JoinModel](
        self,
        model: ty.Type[Model],
        data: tuple[ty.Any, ...],
        join: InnerJoin[JoinModel],
    ) -> tuple[Model, JoinModel]: ...
    @ty.overload
    def _convert_data[Model, JoinModel](
        self,
        model: ty.Type[Model],
        data: tuple[ty.Any, ...],
        join: LeftJoin[JoinModel],
    ) -> tuple[Model, JoinModel | None]: ...
    @ty.overload
    def _convert_data[Model, JoinModel](
        self,
        model: ty.Type[Model],
        data: tuple[ty.Any, ...],
        join: RightJoin[JoinModel],
    ) -> tuple[Model | None, JoinModel]: ...
    @ty.overload
    def _convert_data[Model, JoinModel](
        self,
        model: ty.Type[Model],
        data: tuple[ty.Any, ...],
        join: Join[JoinModel],
    ) -> tuple[Model | None, JoinModel | None]: ...
    @ty.overload
    def _convert_data[Model](
        self, model: ty.Type[Model], data: tuple[ty.Any, ...], join: None = None
    ) -> Model: ...
    def _convert_data[Model, JoinModel](
        self,
        model: ty.Type[Model],
        data: tuple[ty.Any, ...],
        join: Join[JoinModel] | None = None,
    ) -> tuple[Model | None, JoinModel | None] | Model | None:
        """
        Converts raw data from db to model.
        """
        signature = self.signatures[model.__name__]
        if join:
            sep = len(signature.fields)
            return (
                self._convert_data(model, data[:sep]),
                self._convert_data(join.model, data[sep:]),
            )
        elif set(data) == {None}:
            return None

        if len(data) != len(signature.fields):
            raise ValueError(
                f"Model {signature.name} have {len(signature.fields)} fields, "
                f"but {len(data)} given"
            )

        kwargs: dict[str, ty.Any] = {}
        for field, value in zip(signature.fields, data):
            kwargs[field.name] = self.provider.convert_value(
                value, field.python_type
            )

        return model(**kwargs)

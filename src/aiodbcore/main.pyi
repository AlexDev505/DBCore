from __future__ import annotations

import typing as ty

if ty.TYPE_CHECKING:
    from .joins import InnerJoin, Join, LeftJoin, RightJoin
    from .models import Field, ModelSignature
    from .operators import InvertedField, Operator
    from .providers import BaseProvider


class AsyncDBCore[Models]:
    signatures: dict[str, ModelSignature] = ...
    dbs: dict[str, BaseProvider] = ...
    db_names: dict[str, str] = ...

    @classmethod
    def init(
        cls, database_path: str, db_name: str = "main", **connection_kwargs
    ) -> None: ...
    @classmethod
    async def close_connections(cls) -> None: ...
    def __init__(self, db: str = "main"):
        self.provider: BaseProvider = ...

    async def execute(self, query: str, args: ty.Sequence[ty.Any] = ()): ...
    async def create_tables(self) -> None: ...
    @ty.overload
    async def insert[Model](self, obj: Model, /) -> Model: ...
    @ty.overload
    async def insert[Model](self, objs: list[Model], /) -> list[Model]: ...
    def _prepare_select_query(
        self,
        model_name: str,
        join: Join[Models] | None = None,
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> str: ...
    @ty.overload
    def _convert_data[Model](
        self, model: ty.Type[Model], data: tuple[ty.Any, ...], join: None = None
    ) -> Model: ...
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
    async def fetchone[Model](
        self,
        model: ty.Type[Model],
        *,
        join: None = None,
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> Model | None: ...
    @ty.overload
    async def fetchone[Model, JoinModel](
        self,
        model: ty.Type[Model],
        *,
        join: InnerJoin[JoinModel],
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[Model, JoinModel] | None: ...
    @ty.overload
    async def fetchone[Model, JoinModel](
        self,
        model: ty.Type[Model],
        *,
        join: LeftJoin[JoinModel],
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[Model, JoinModel | None] | None: ...
    @ty.overload
    async def fetchone[Model, JoinModel](
        self,
        model: ty.Type[Model],
        *,
        join: RightJoin[JoinModel],
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[Model | None, JoinModel] | None: ...
    @ty.overload
    async def fetchall[Model](
        self,
        model: ty.Type[Model],
        *,
        join: None = None,
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Model]: ...
    @ty.overload
    async def fetchall[Model, JoinModel](
        self,
        model: ty.Type[Model],
        *,
        join: InnerJoin[JoinModel],
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[tuple[Model, JoinModel]]: ...
    @ty.overload
    async def fetchall[Model, JoinModel](
        self,
        model: ty.Type[Model],
        *,
        join: LeftJoin[JoinModel],
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[tuple[Model, JoinModel | None]]: ...
    @ty.overload
    async def fetchall[Model, JoinModel](
        self,
        model: ty.Type[Model],
        *,
        join: RightJoin[JoinModel],
        where: Operator | None = None,
        order_by: (
            Field | InvertedField | tuple[Field | InvertedField, ...] | None
        ) = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[tuple[Model | None, JoinModel]]: ...
    async def save(self, obj: Models, /) -> None: ...
    async def update[T](
        self,
        model: ty.Type[Models],
        fields: dict[Field[T], T],
        *,
        where: Operator | None = None,
    ) -> None: ...
    async def delete(
        self, model: ty.Type[Models], *, where: Operator | None
    ) -> None: ...
    async def drop_table(self, model: ty.Type[Models], /) -> None: ...

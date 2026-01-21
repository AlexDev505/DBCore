from __future__ import annotations

import typing as ty

if ty.TYPE_CHECKING:
    from .core import BaseDBCore
    from .joins import InnerJoin, LeftJoin, RightJoin
    from .models import Field
    from .operators import InvertedField, Operator
    from .providers import BaseAsyncProvider


class AsyncDBCore[Models](BaseDBCore[BaseAsyncProvider, Models]):
    @classmethod
    async def close_connections(cls) -> None: ...
    async def execute(self, query, args=()): ...
    async def create_tables(self) -> None: ...
    @ty.overload
    async def insert[Model](self, objs: list[Model], /) -> list[Model]: ...
    @ty.overload
    async def insert[Model](self, obj: Model, /) -> Model: ...
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
        limit: int | None = None,
        offset: int = 0,
    ) -> list[tuple[Model | None, JoinModel]]: ...
    async def save(self, obj) -> None: ...
    async def update(self, model, fields, *, where=None) -> None: ...
    async def delete(self, model, *, where) -> None: ...
    async def drop_table(self, model, /) -> None: ...

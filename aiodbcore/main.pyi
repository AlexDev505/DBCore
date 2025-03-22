from __future__ import annotations

import typing as ty


if ty.TYPE_CHECKING:
    from .models import ModelField
    from .models import ModelSignature
    from .operators import Operator
    from .providers import BaseProvider
    from .joins import Join, InnerJoin, LeftJoin, RightJoin

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
    async def insert[Model](self, obj: Model) -> Model: ...
    def _prepare_select_query(
        self,
        model_name: str,
        join: Join[Models] | None = None,
        where: Operator | None = None,
        order_by: ModelField | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> str: ...
    def _convert_data(
        self,
        model: ty.Type[Models],
        data: tuple[ty.Any],
        join: Join[Models] | None = None,
    ) -> Models | tuple[Models | None, Models | None]: ...
    @ty.overload
    async def fetchone[Model](
        self,
        model: ty.Type[Model],
        *,
        join: None = None,
        where: Operator | None = None,
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
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
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
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
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
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
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[Model | None, JoinModel] | None: ...
    async def fetchone(
        self,
        model: ty.Type[Models],
        *,
        join: Join[Models] | None = None,
        where: Operator | None = None,
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> ty.Any: ...
    @ty.overload
    async def fetchall[Model](
        self,
        model: ty.Type[Model],
        *,
        join: None = None,
        where: Operator | None = None,
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
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
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
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
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
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
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[tuple[Model | None, JoinModel]]: ...
    async def fetchall(
        self,
        model: ty.Type[Models],
        *,
        join: Join[Models] | None = None,
        where: Operator | None = None,
        order_by: ty.Annotated[ty.Any, ModelField] | None = None,
        reverse: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> ty.Any: ...
    async def save(self, obj: Models) -> None: ...
    async def update(
        self,
        model: ty.Type[Models],
        fields: dict[ty.Any, ty.Any],
        *,
        where: Operator | None = None,
    ) -> None: ...
    async def delete(
        self, model: ty.Type[Models], *, where: Operator | None
    ) -> None: ...
    async def drop_table(self, model: ty.Type[Models]) -> None: ...

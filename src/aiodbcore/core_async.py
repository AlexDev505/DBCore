from .core import BaseDBCore
from .providers import BaseAsyncProvider


class AsyncDBCore[Models](BaseDBCore[BaseAsyncProvider, Models]):
    """
    Main async db class.
    You can implement your queries to the database in the child class
    or use this class directly.
    """

    _use_async = True

    @classmethod
    async def close_connections(cls) -> None:
        for provider in cls.dbs.values():
            if isinstance(provider, BaseAsyncProvider):
                await provider.close_connection()

    async def execute(self, query, args=()):
        return await self.provider.execute(query, args)

    async def create_tables(self) -> None:
        for signature in self.signatures.values():
            await self.provider.executescript(
                self._prepare_create_table_query(signature)
            )

    async def insert(self, objs, /) -> Models | list[Models]:
        obj_ids = await self.provider.execute_insert_query(
            *self._prepare_insert_query(objs)
        )
        return self._assign_ids(objs, obj_ids)

    async def fetchone(
        self,
        model,
        *,
        join=None,
        where=None,
        order_by=None,
        limit=None,
        offset=0,
    ):
        if data := await self.provider.fetchone(
            *self._prepare_select_query(
                model.__name__, None, join, where, order_by, limit, offset
            )
        ):
            return self._convert_data(model, data, join)

    async def fetchall(
        self,
        model,
        *,
        join=None,
        where=None,
        order_by=None,
        limit=None,
        offset=0,
    ):
        data = await self.provider.fetchall(
            *self._prepare_select_query(
                model.__name__, None, join, where, order_by, limit, offset
            )
        )
        return (
            [self._convert_data(model, obj, join) for obj in data]
            if data
            else []
        )

    async def save(self, obj) -> None:
        if (query := self._prepare_save_query(obj)) is not None:
            return await self.execute(*query)

    async def update(self, model, fields, *, where=None) -> None:
        await self.execute(*self._prepare_update_query(model, fields, where))

    async def delete(self, model, *, where) -> None:
        await self.execute(*self._prepare_delete_query(model, where))

    async def drop_table(self, model, /) -> None:
        """
        Drops table from db.
        :param model: model to drop.
        """
        await self.execute(self._prepare_drop_table_query(model))

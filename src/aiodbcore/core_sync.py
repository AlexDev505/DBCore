from .core import BaseDBCore
from .providers import BaseSyncProvider


class SyncDBCore[Models](BaseDBCore[BaseSyncProvider, Models]):
    """
    Main sync db class.
    You can implement your queries to the database in the child class
    or use this class directly.
    """

    @classmethod
    def close_connections(cls) -> None:
        for provider in cls.dbs.values():
            provider.close_connection()

    def execute(self, query, args=()):
        return self.provider.execute(query, args)

    def create_tables(self) -> None:
        for signature in self.signatures.values():
            self.provider.executescript(
                self._prepare_create_table_query(signature)
            )

    def insert(self, objs, /) -> Models | list[Models]:
        obj_ids = self.provider.execute_insert_query(
            *self._prepare_insert_query(objs)
        )
        return self._assign_ids(objs, obj_ids)

    def fetchone(
        self,
        model,
        *,
        join=None,
        where=None,
        order_by=None,
        limit=None,
        offset=0,
    ):
        if data := self.provider.fetchone(
            *self._prepare_select_query(
                model.__name__, None, join, where, order_by, limit, offset
            )
        ):
            return self._convert_data(model, data, join)

    def fetchall(
        self,
        model,
        *,
        join=None,
        where=None,
        order_by=None,
        limit=None,
        offset=0,
    ):
        data = self.provider.fetchall(
            *self._prepare_select_query(
                model.__name__, None, join, where, order_by, limit, offset
            )
        )
        return (
            [self._convert_data(model, obj, join) for obj in data]
            if data
            else []
        )

    def save(self, obj) -> None:
        if (query := self._prepare_save_query(obj)) is not None:
            return self.execute(*query)

    def update(self, model, fields, *, where=None) -> None:
        self.execute(*self._prepare_update_query(model, fields, where))

    def delete(self, model, *, where) -> None:
        self.execute(*self._prepare_delete_query(model, where))

    def drop_table(self, model, /) -> None:
        """
        Drops table from db.
        :param model: model to drop.
        """
        self.execute(self._prepare_drop_table_query(model))

import asyncio
import re
import typing as ty

from ...exceptions import UniqueRequiredError

try:
    import asyncpg
except ModuleNotFoundError as err:
    raise RuntimeError(
        "You should install `asyncpg` backend to connect to this db. "
        "Use `pip install asyncpg`"
    ) from err

from ..base import BaseProvider, PoolConnectionWrapper


class AsyncpgProvider(BaseProvider[asyncpg.Connection]):
    CREATE_TABLE_QUERY_TEMPLATE = (
        'CREATE TABLE IF NOT EXISTS "{table_name}" '
        "(id SERIAL PRIMARY KEY NOT NULL, {fields})"
    )
    INSERT_INTO_QUERY_TEMPLATE = (
        'INSERT INTO "{table_name}" ({fields}) VALUES {rows} RETURNING id'
    )

    DEFAULT_FIELD_TYPE = "BYTEA"
    PLACEHOLDER: ty.Callable[[int], str] = staticmethod(lambda i: f"${i}")

    def __init__(self, db_path, **connection_kwargs) -> None:
        super().__init__(db_path, **connection_kwargs)
        self.connections_pool = None
        self._pool_init_lock = asyncio.Lock()

    async def create_connection(self) -> None:
        self.connections_pool = await asyncpg.create_pool(
            self.db_path, min_size=1, max_size=5
        )

    async def close_connection(self) -> None:
        await self.connections_pool.close()

    def ensure_connection(self):
        return PoolConnectionWrapper(self, self._pool_init_lock)

    async def _execute(self, query, args=()):
        async with self.ensure_connection() as connection:
            return await connection.execute(query, *args)

    async def _execute_insert_query(self, query, values) -> list[int]:
        async with self.ensure_connection() as connection:
            rows = await connection.fetch(query, *values)
            return [row.get("id") for row in rows]

    async def _fetchone(self, query, args=()) -> tuple[ty.Any]:
        async with self.ensure_connection() as connection:
            return await connection.fetchrow(query, *args)

    async def _fetchall(self, query, args=()) -> list[tuple[ty.Any]]:
        async with self.ensure_connection() as connection:
            return await connection.fetch(query, *args)

    @staticmethod
    def modify_db_path(db_path: str) -> str:
        return re.sub(r"\+asyncpg", "", db_path)

    def _translate_exception(self, exception, query, params):
        if isinstance(exception, asyncpg.UniqueViolationError):
            if match := re.search(
                r"Key \((.+?)\)=", getattr(exception, "detail", "")
            ):
                return UniqueRequiredError(
                    query, params, exception, field_name=match.group(1)
                )
        return super()._translate_exception(exception, query, params)

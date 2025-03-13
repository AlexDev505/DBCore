import asyncio
import typing as ty

try:
    import aiosqlite
except ModuleNotFoundError as err:
    raise RuntimeError(
        "You should install `aiosqlite` backend to connect to this db. "
        "Use `pip install aiosqlite`"
    ) from err

from ..base import BaseProvider, ConnectionWrapper


class AiosqliteProvider(BaseProvider[aiosqlite.Connection]):
    def __init__(self, db_path, **connection_kwargs) -> None:
        super().__init__(db_path, **connection_kwargs)
        self.connection = None
        self._lock = asyncio.Lock()

    async def create_connection(self) -> None:
        if not self.connection:
            self.connection = await aiosqlite.connect(
                self.db_path, isolation_level=None
            )

    async def close_connection(self) -> None:
        if self.connection:
            await self.connection.close()
            self.connection = None

    def ensure_connection(self):
        return ConnectionWrapper(self, self._lock)

    async def _execute(self, query, args=()):
        async with self.ensure_connection() as connection:
            return await connection.execute(query, args)

    async def _execute_insert_query(self, query, values):
        async with self.ensure_connection() as connection:
            row = await connection.execute_insert(query, values)
            return row[0]

    async def _fetchone(
        self, query: str, args: ty.Iterable[ty.Any] = ()
    ) -> tuple[ty.Any] | None:
        if rows := await self._fetchall(query, args):
            return rows[0]

    async def _fetchall(
        self, query: str, args: ty.Iterable[ty.Any] = ()
    ) -> list[tuple[ty.Any]]:
        async with self.ensure_connection() as connection:
            return list(await connection.execute_fetchall(query, args))

    @staticmethod
    def modify_db_path(db_path: str) -> str:
        return db_path.removeprefix("sqlite+aiosqlite://")

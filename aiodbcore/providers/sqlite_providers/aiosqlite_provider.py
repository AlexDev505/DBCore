import asyncio
import typing as ty

from ...exceptions import UniqueRequiredError

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
            cursor: aiosqlite.Cursor = await connection.execute(query, values)
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def _fetchone(self, query, args=()) -> tuple[ty.Any] | None:
        if rows := await self._fetchall(query, args):
            return rows[0]

    async def _fetchall(self, query, args=()) -> list[tuple[ty.Any]]:
        async with self.ensure_connection() as connection:
            return list(await connection.execute_fetchall(query, args))

    @staticmethod
    def modify_db_path(db_path: str) -> str:
        return db_path.removeprefix("sqlite+aiosqlite://")

    def _translate_exception(self, exception, query, params):
        if isinstance(exception, aiosqlite.IntegrityError):
            if exception.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
                text = exception.args[0]
                return UniqueRequiredError(
                    query,
                    params,
                    exception,
                    field_name=text[text.rfind(": ") + 2 :],
                )
        return super()._translate_exception(exception, query, params)

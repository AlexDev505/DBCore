import threading
import typing as ty

from ...exceptions import UniqueRequiredError

try:
    import sqlite3
except ModuleNotFoundError as err:
    raise RuntimeError(
        "You should install `sqlite3` backend to connect to this db. "
    ) from err

from ..base_sync import BaseSyncProvider, SyncConnectionWrapper


class Sqlite3Provider(BaseSyncProvider[sqlite3.Connection]):
    def __init__(self, db_path, **connection_kwargs) -> None:
        super().__init__(db_path, **connection_kwargs)
        self.connection = None
        self._lock = threading.Lock()

    def create_connection(self) -> None:
        if not self.connection:
            self.connection = sqlite3.connect(
                self.db_path, isolation_level=None
            )

    def close_connection(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def ensure_connection(self) -> SyncConnectionWrapper[sqlite3.Connection]:
        return SyncConnectionWrapper(self, self._lock)

    def _execute(self, query, args=()):
        with self.ensure_connection() as connection:
            return connection.execute(query, args)

    def executescript(self, query):
        with self.ensure_connection() as connection:
            return connection.executescript(query)

    def _fetchone(self, query, args=()) -> tuple[ty.Any] | None:
        if rows := self._fetchall(query, args):
            return rows[0]

    def _fetchall(self, query, args=()) -> list[tuple[ty.Any]]:
        with self.ensure_connection() as connection:
            return list(connection.execute(query, args).fetchall())

    @staticmethod
    def modify_db_path(db_path: str) -> str:
        return db_path.removeprefix("sqlite+sqlite3://")

    def _translate_exception(self, exception, query, params):
        if isinstance(exception, sqlite3.IntegrityError):
            if exception.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
                text = exception.args[0]
                return UniqueRequiredError(
                    query,
                    params,
                    exception,
                    field_name=text[text.rfind(": ") + 2 :],
                )
        return super()._translate_exception(exception, query, params)

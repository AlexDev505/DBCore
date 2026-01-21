import importlib
import re
import typing as ty

from .base import BaseProvider
from .base_async import BaseAsyncProvider as BaseAsyncProvider
from .base_sync import BaseSyncProvider as BaseSyncProvider

__providers__ = {
    "sqlite": {"sync": "sqlite3", "async": "aiosqlite"},
    "postgresql": {"async": "asyncpg"},
}


def get_provider(
    db_path: str, *, use_async: bool = False
) -> ty.Type[BaseProvider]:
    """
    Imports suitable provider class and returns it.
    :param db_path: path to db.
    :returns: provider class.
    """
    if not (
        match := re.fullmatch(
            r"(?P<provider>.+?)(\+(?P<library>.+?))?://(?P<db>.+)", db_path
        )
    ):
        raise ValueError(
            "Invalid db path. pass it like `sqlite+aiosqlite://db.path`"
        )
    provider = match.group("provider")
    library = match.group("library")
    if provider == "postgres":
        provider = "postgresql"

    if provider not in __providers__:
        raise ValueError(f"`{provider}` not supported")
    if not library:
        library = __providers__[provider]["async" if use_async else "sync"]
    elif library not in __providers__[provider].values():
        raise ValueError(f"`{library}` not supported")
    elif library in __providers__[provider]["async"] and not use_async:
        raise ValueError(f"DB {db_path} uses only async library")
    elif library in __providers__[provider]["sync"] and use_async:
        raise ValueError(f"DB {db_path} uses only sync library")

    try:
        module = importlib.import_module(
            f".{library}_provider", package=f"{__name__}.{provider}_providers"
        )
    except ModuleNotFoundError as err:
        raise ValueError(f"`{provider}` or `{library}` not supported") from err

    return getattr(module, f"{library.capitalize()}Provider")

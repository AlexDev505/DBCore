import importlib
import re
import typing as ty

from .base import BaseProvider


def get_provider(db_url: str) -> ty.Type[BaseProvider]:
    """
    Imports suitable provider class and returns it.
    :param db_url: path to db.
    :returns: provider class.
    """
    if not (
        match := re.fullmatch(
            r"(?P<provider>.+?)(\+(?P<library>.+?))?://(?P<db>.+)", db_url
        )
    ):
        raise ValueError(
            "Invalid db url. pass url like `sqlite+aiosqlite://db.path`"
        )
    provider = match.group("provider")
    library = match.group("library")
    if provider == "postgres":
        provider = "postgresql"

    try:
        module = importlib.import_module(
            f".{library}_provider", package=f"{__name__}.{provider}_providers"
        )
    except ModuleNotFoundError as err:
        raise ValueError(f"`{provider}` or `{library}` not supported") from err

    return getattr(module, f"{library.capitalize()}Provider")

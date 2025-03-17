import typing as ty
from dataclasses import dataclass

from aiodbcore.models import FieldMod


@dataclass
class User:
    id: int | None = None
    name: str = ""
    age: int = 0
    moneys: int = 1000


@dataclass
class Chat:
    id: int | None = None
    title: ty.Annotated[str, FieldMod.UNIQUE] = ""  # Values in db must be unique

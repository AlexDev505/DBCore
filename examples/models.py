import typing as ty
from dataclasses import dataclass

from aiodbcore.models import Field, FieldMod


@dataclass
class User:
    id: Field[int | None] = Field(None)
    name: Field[str] = Field("")
    age: Field[int] = Field(0)
    moneys: Field[int] = Field(1000)


@dataclass
class Chat:
    id: Field[int | None] = Field(None)
    title: ty.Annotated[Field[str], FieldMod.UNIQUE] = Field(
        ""
    )  # Values in db must be unique

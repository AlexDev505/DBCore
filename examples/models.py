import datetime
import typing as ty
from dataclasses import dataclass, field

from aiodbcore.models import Field, FieldMod, SpecificSQLType


@dataclass
class User:
    id: Field[int | None] = Field(None)
    name: Field[str] = Field("")
    age: Field[int] = Field(0)
    moneys: ty.Annotated[Field[int], SpecificSQLType("BIGINT")] = Field(1000)
    registered_at: Field[datetime.datetime] = Field(
        field(default_factory=datetime.datetime.now)
    )


@dataclass
class Chat:
    id: Field[int | None] = Field(None)
    title: ty.Annotated[Field[str], FieldMod.UNIQUE] = Field(
        ""
    )  # Values in db must be unique

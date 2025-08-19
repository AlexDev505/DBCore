from __future__ import annotations

import typing as ty
from abc import ABC

if ty.TYPE_CHECKING:
    from .models import Field


class Join[T](ABC):
    type: str

    def __init__(
        self,
        model: ty.Type[T],
        on: tuple[Field, Field],
    ):
        self.model = model
        self.on: tuple[Field, Field] = on

    def __repr__(self):
        return (
            f'{self.type} JOIN "{self.model.__name__.lower()}" ON '
            f"{self.on[0].model_name.lower()}.{self.on[0].name.lower()}="
            f"{self.on[1].model_name.lower()}.{self.on[1].name.lower()}"
        )

    __str__ = __repr__


class InnerJoin[T](Join[T]):
    type = "INNER"


class RightJoin[T](Join[T]):
    type = "RIGHT"


class LeftJoin[T](Join[T]):
    type = "LEFT"

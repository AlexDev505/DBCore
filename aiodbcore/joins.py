from __future__ import annotations

import typing as ty
from abc import ABC


if ty.TYPE_CHECKING:
    from .models import ModelField


class Join[T](ABC):
    type: str

    def __init__(
        self,
        model: ty.Type[T],
        on: tuple[ty.Annotated[ty.Any, ModelField], ty.Annotated[ty.Any, ModelField]],
    ):
        self.model = model
        self.on: tuple[ModelField, ModelField] = on

    def __repr__(self):
        return (
            f'{self.type} JOIN "{self.model.__name__.lower()}" ON '
            f"{self.on[0].field.model_name.lower()}.{self.on[0].field.name.lower()}="
            f"{self.on[1].field.model_name.lower()}.{self.on[1].field.name.lower()}"
        )

    __str__ = __repr__


class InnerJoin(Join):
    type = "INNER"


class RightJoin(Join):
    type = "RIGHT"


class LeftJoin(Join):
    type = "LEFT"

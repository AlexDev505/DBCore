from __future__ import annotations

import dataclasses
import types as tys
import typing as ty
from contextlib import suppress
from datetime import datetime, date, time
from enum import Enum
from functools import wraps
from inspect import isclass

from .operators import (
    CmpOperator,
    EqCmpOperator,
    NeCmpOperator,
    LtCmpOperator,
    LeCmpOperator,
    GtCmpOperator,
    GeCmpOperator,
    ContainedCmpOperator,
    IsNullCmpOperator,
)
from .tools import watch_changes


LT_GT_SUPPORTED = {int, float, datetime, date, time}


@dataclasses.dataclass
class Field:
    """
    Field of model.
    Contains name and python type.
    """

    model_name: str
    name: str
    python_type: ty.Type
    unique: bool = False

    def compare_type(self, type_: ty.Any) -> bool:
        """
        Checks whether the field can be the specified type.
        """
        if isinstance(self.python_type, UnionType):
            return self.python_type.is_contains_type(type_)
        return type_ is self.python_type

    def __repr__(self):
        type_name = (
            self.python_type.__name__
            if isclass(self.python_type)
            else repr(self.python_type)
        )
        return f"<Field {self.model_name}{self.name}:{type_name}>"


@dataclasses.dataclass
class ModelSignature:
    """
    Signature of model.
    Contains name and information about fields.
    """

    name: str
    fields: list[Field] = dataclasses.field(default_factory=list)


class UnionType:
    """
    type of field that can take different data types.
    """

    def __init__(self, *types: ty.Any):
        self.types = list(types)
        self.nullable = tys.NoneType in self.types
        if self.nullable:
            self.types.remove(tys.NoneType)

    def __call__(self, obj: ty.Any) -> ty.Any:
        """
        Wrapping obj to suitable data type.
        """
        for type_ in self.types:
            with suppress(ValueError, TypeError):
                return type_(obj)

    def is_contains_type(self, type_: ty.Type) -> bool:
        return type_ in self.types or (self.nullable and type_ is tys.NoneType)

    def __repr__(self):
        return (
            f"{"|".join(map(lambda x: x.__name__, self.types))}"
            f"{"|None" if self.nullable else ""}"
        )


def prepare_model(model: ty.Type) -> ModelSignature:
    """
    Prepares model to work in db context.
    Wraps model into `watch_changes`.
    Replaces class attributes onto `ModelField` instances.
    :param model: dataclass.
    :returns: signature of model.
    """
    if not dataclasses.is_dataclass(model):
        raise TypeError(f"Model `{model.__name__}` is not a dataclass")
    watch_changes(model)
    signature = ModelSignature(model_name := model.__name__)
    for field_name, field_type in ty.get_type_hints(model, include_extras=True).items():
        unique = False
        if ty.get_origin(field_type) is ty.Annotated:
            metadata = field_type.__metadata__
            unique = FieldMod.UNIQUE in metadata
            field_type = ty.get_args(field_type)[0]
        lt_gt = field_type in LT_GT_SUPPORTED
        if ty.get_origin(field_type) in {ty.Union, tys.UnionType}:
            field_type = UnionType(*ty.get_args(field_type))
            lt_gt = any(field_type.is_contains_type(x) for x in LT_GT_SUPPORTED)
        field = Field(model_name, field_name, field_type, unique)
        signature.fields.append(field)
        setattr(
            model,
            field_name,
            ModelField(field, getattr(model, field_name, None), lt_gt=lt_gt),
        )
    if (id_field := signature.fields[0]).name != "id":
        raise AttributeError(
            f"The first attribute of the model `{model.__name__}` should be `id`"
        )
    if not id_field.compare_type(int):
        raise TypeError(
            f"`id` attribute of model `{model.__name__}` should contains `int`"
        )

    return signature


def field_operator(
    func: ty.Callable[[ModelField, ty.Any], CmpOperator],
) -> ty.Callable[[ModelField, ty.Any], CmpOperator]:
    """
    Decorator for `ModelField` comparing operators.
    Checks is operator available for this field.
    Returns suitable instance of `Operator` class.
    """
    naming_map = {
        "__eq__": ("eq", EqCmpOperator),
        "__ne__": ("eq", NeCmpOperator),
        "contained": ("eq", ContainedCmpOperator),
        "is_null": ("eq", IsNullCmpOperator),
        "__lt__": ("lt_gt", LtCmpOperator),
        "__le__": ("lt_gt", LeCmpOperator),
        "__gt__": ("lt_gt", GtCmpOperator),
        "__ge__": ("lt_gt", GeCmpOperator),
    }

    @wraps(func)
    def _wrapper(self: ModelField, other: ty.Any = None) -> CmpOperator:
        op = naming_map[func.__name__]
        field = self.field
        if not getattr(self, op[0]):
            raise TypeError(f"{field} does not support {func.__name__} operator")
        if op[1] is ContainedCmpOperator:  # checks type of all elements
            for el in other:
                if not field.compare_type(type(el)):
                    raise TypeError(f"unable to compare {field} and `{el}`")
        elif op[1] is not IsNullCmpOperator:
            if not field.compare_type(type(other)):
                raise TypeError(f"unable to compare {field} and `{other}`")

        return op[1](f"{field.model_name.lower()}.{field.name}", other)

    return _wrapper


class ModelField:
    """
    Params of model field.
    """

    def __init__(
        self,
        field: Field,
        default_value: ty.Any,
        eq: bool = True,
        lt_gt: bool = False,
    ):
        """
        :param field: `Field` instance.
        :param default_value: Default value of this field.
        :param eq: Is equation operators available for this field.
        :param lt_gt: If comparing operators available for this field.
        """
        self.field = field
        self.default_value = default_value
        self.eq = eq
        self.lt_gt = lt_gt

    @field_operator
    def __eq__(self, other) -> EqCmpOperator:
        pass

    @field_operator
    def __ne__(self, other) -> NeCmpOperator:
        pass

    @field_operator
    def __lt__(self, other) -> LtCmpOperator:
        pass

    @field_operator
    def __le__(self, other) -> LeCmpOperator:
        pass

    @field_operator
    def __gt__(self, other) -> GtCmpOperator:
        pass

    @field_operator
    def __ge__(self, other) -> GeCmpOperator:
        pass

    @field_operator
    def contained(self, sequence: list | tuple) -> ContainedCmpOperator:
        pass

    @field_operator
    def is_null(self) -> IsNullCmpOperator:
        pass

    def __hash__(self):
        return hash(self.field.name)

    def __repr__(self):
        return f"<ModelField {self.default_value!r}>"


class FieldMod(Enum):
    UNIQUE = "unique"

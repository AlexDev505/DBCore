from __future__ import annotations

import dataclasses
import types as tys
import typing as ty
from contextlib import suppress
from datetime import date, datetime, time
from enum import Enum
from functools import wraps
from inspect import isclass

from .operators import (
    CmpOperator,
    ContainedCmpOperator,
    EqCmpOperator,
    GeCmpOperator,
    GtCmpOperator,
    InvertedField,
    IsNullCmpOperator,
    LeCmpOperator,
    LtCmpOperator,
    NeCmpOperator,
)
from .tools import watch_changes

LT_GT_SUPPORTED = {int, float, datetime, date, time}


def field_operator[T, **P, RT: CmpOperator](
    func: ty.Callable[ty.Concatenate[Field[T], P], ty.Type[RT]],
) -> ty.Callable[ty.Concatenate[Field[T], P], RT]:
    """
    Decorator for `Field` comparing operators.
    Check operator is available for this field.
    Returns suitable instance of `Operator` class.
    """
    naming_map = {
        "__eq__": "eq",
        "__ne__": "eq",
        "contained": "eq",
        "is_null": "eq",
        "__lt__": "lt_gt",
        "__le__": "lt_gt",
        "__gt__": "lt_gt",
        "__ge__": "lt_gt",
    }

    @wraps(func)
    def _wrapper(self: Field[T], *args: P.args, **kwargs: P.kwargs) -> RT:
        other = args[0] if args else kwargs.get("other")
        op_name = naming_map[func.__name__]
        if not self.inited:
            raise RuntimeError(f"Model '{self.model_name}' is not initialized")
        if not getattr(self, op_name):
            raise TypeError(
                f"{self!r} does not support {func.__name__} operator"
            )
        elif (op := func(self, *args, **kwargs)) not in {
            IsNullCmpOperator,
            ContainedCmpOperator,
        }:
            if not self.compare_type(type(other)):
                raise TypeError(f"unable to compare {self!r} and {other!r}")
        return op(str(self), other)

    return _wrapper


class Field[T]:
    def __init__(self, default_value: T):
        self.default_value = default_value
        self._first = True

        self.inited: bool = False
        self.model_name: str = ""
        self.name: str = ""
        self.python_type: ty.Type[T] | UnionType[T] | None = None
        self.unique: bool | None = None
        self.eq: bool | None = None
        self.lt_gt: bool | None = None

    def __set_name__(self, owner: type, name: str):
        self.model_name = owner.__name__
        self.name = name

    def __get__(self, obj: object | None, owner: type):
        if self._first:
            self._first = False
            return self.default_value
        if obj is None:
            return self
        return obj.__dict__[self.name]

    def __set__(self, obj, value: T):
        obj.__dict__[self.name] = value

    def init(
        self,
        model_name: str,
        name: str,
        python_type: ty.Type[T] | UnionType[T],
        unique: bool = False,
        eq: bool = True,
        lt_gt: bool = False,
    ) -> None:
        """
        Initialize `Field` instance.

        :param model_name: Name of the model.
        :param name: Name of the field.
        :param python_type: Type of the field.
        :param default_value: Default value of this field.
        :param unique: Is this field unique?
        :param eq: Are equation operators available for this field?
        :param lt_gt: Are comparing operators available for this field?
        """
        self.model_name = model_name
        self.name = name
        self.python_type = python_type
        self.unique = unique
        self.eq = eq
        self.lt_gt = lt_gt
        self.inited = True

    def compare_type(self, type_: ty.Any) -> bool:
        """
        Checks whether the field can be the specified type.
        """
        if isinstance(self.python_type, UnionType):
            return self.python_type.is_contains_type(type_)
        return type_ is self.python_type

    @field_operator
    def __eq__(self, other: T) -> ty.Type[EqCmpOperator]:
        return EqCmpOperator

    @field_operator
    def __ne__(self, other: T) -> ty.Type[NeCmpOperator]:
        return NeCmpOperator

    @field_operator
    def __lt__(self, other: T) -> ty.Type[LtCmpOperator]:
        return LtCmpOperator

    @field_operator
    def __le__(self, other: T) -> ty.Type[LeCmpOperator]:
        return LeCmpOperator

    @field_operator
    def __gt__(self, other: T) -> ty.Type[GtCmpOperator]:
        return GtCmpOperator

    @field_operator
    def __ge__(self, other: T) -> ty.Type[GeCmpOperator]:
        return GeCmpOperator

    @field_operator
    def contained(
        self, sequence: list[T] | tuple[T, ...]
    ) -> ty.Type[ContainedCmpOperator]:
        for el in sequence:
            if not self.compare_type(type(el)):
                raise TypeError(f"unable to compare {self!r} and `{el!r}`")
        return ContainedCmpOperator

    @field_operator
    def is_null(self) -> ty.Type[IsNullCmpOperator]:
        return IsNullCmpOperator

    def __invert__(self) -> InvertedField:
        return InvertedField(str(self))

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f"{self.model_name}.{self.name}"

    def __repr__(self):
        type_name = (
            self.python_type.__name__
            if isclass(self.python_type)
            else repr(self.python_type)
        )
        return f"<Field {self}:{type_name}>"


@dataclasses.dataclass
class ModelSignature:
    """
    Signature of a model.
    Contains name and information about fields.
    """

    name: str
    fields: list[Field] = dataclasses.field(default_factory=list)


class UnionType[T: ty.Any]:
    """
    type of field that can take different data types.
    """

    def __init__(self, *types: ty.Type[T]):
        self.types = list(types)
        self.nullable = tys.NoneType in self.types
        if self.nullable:
            self.types.remove(tys.NoneType)  # type: ignore

    def __call__(self, obj: ty.Any) -> T:
        """
        Wrapping obj to suitable data type.
        """
        for type_ in self.types:
            with suppress(ValueError, TypeError):
                return type_(obj)
        raise ValueError(f"`{obj}` cant be {self}")

    def is_contains_type(self, type_: ty.Type) -> bool:
        return type_ in self.types or (self.nullable and type_ is tys.NoneType)

    def __repr__(self) -> str:
        return (
            f"{'|'.join(map(lambda x: x.__name__, self.types))}"
            f"{'|None' if self.nullable else ''}"
        )


def prepare_model(model: ty.Type[ty.Any]) -> ModelSignature:
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
    for field_name, field_type in ty.get_type_hints(
        model, include_extras=True
    ).items():
        unique = False
        if ty.get_origin(field_type) is ty.Annotated:
            metadata = field_type.__metadata__
            unique = FieldMod.UNIQUE in metadata
            field_type = ty.get_args(field_type)[0]
        if ty.get_origin(field_type) is Field:
            field = getattr(model, field_name, None)
            if not isinstance(field, Field):
                field = Field(getattr(model, field_name, None))
            field_type = ty.get_args(field_type)[0]
        else:
            field = Field(getattr(model, field_name, None))
        lt_gt = field_type in LT_GT_SUPPORTED
        if ty.get_origin(field_type) in {ty.Union, tys.UnionType}:
            field_type = UnionType(*ty.get_args(field_type))
            lt_gt = any(field_type.is_contains_type(x) for x in LT_GT_SUPPORTED)
        field.init(model_name, field_name, field_type, unique, True, lt_gt)
        signature.fields.append(field)
        setattr(model, field_name, field)
        getattr(model, field_name)
    if (id_field := signature.fields[0]).name != "id":
        raise AttributeError(
            f"The first attribute of the model `{model.__name__}` should be `id`"
        )
    if not id_field.compare_type(int):
        raise TypeError(
            f"`id` attribute of model `{model.__name__}` should contains `int`"
        )

    return signature


class FieldMod(Enum):
    UNIQUE = "unique"

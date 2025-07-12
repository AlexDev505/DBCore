import dataclasses
import typing as ty
from enum import Enum

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


def field_operator[T, **P, RT: CmpOperator](
    func: ty.Callable[P, ty.Type[RT]],
) -> ty.Callable[P, RT]: ...


class Field[T]:
    def __init__(self, default_value: T):
        self.default_value: T

        self.inited: bool
        self.model_name: str
        self.name: str
        self.python_type: ty.Type[T] | UnionType[T]
        self.unique: bool
        self.eq: bool
        self.lt_gt: bool

    @ty.overload
    def __get__(self, obj: None, owner: type) -> ty.Self: ...
    @ty.overload
    def __get__(self, obj: object, owner: type) -> T: ...
    def __set__(self, obj: object, value: T) -> None: ...
    def init(
        self,
        model_name: str,
        name: str,
        python_type: ty.Type[T] | UnionType[T],
        unique: bool = False,
        eq: bool = True,
        lt_gt: bool = False,
    ) -> None: ...
    def compare_type(self, type_: ty.Any) -> bool: ...
    @field_operator
    def __eq__(self, other: T) -> ty.Type[EqCmpOperator]: ...
    @field_operator
    def __ne__(self, other: T) -> ty.Type[NeCmpOperator]: ...
    @field_operator
    def __lt__(self, other: T) -> ty.Type[LtCmpOperator]: ...
    @field_operator
    def __le__(self, other: T) -> ty.Type[LeCmpOperator]: ...
    @field_operator
    def __gt__(self, other: T) -> ty.Type[GtCmpOperator]: ...
    @field_operator
    def __ge__(self, other: T) -> ty.Type[GeCmpOperator]: ...
    @field_operator
    def contained(
        self, sequence: list[T] | tuple[T, ...]
    ) -> ty.Type[ContainedCmpOperator]: ...
    @field_operator
    def is_null(self) -> ty.Type[IsNullCmpOperator]: ...
    def __invert__(self) -> InvertedField: ...
    def __hash__(self): ...
    def __str__(self): ...
    def __repr__(self): ...


@dataclasses.dataclass
class ModelSignature:
    name: str
    fields: list[Field]


class UnionType[T: ty.Any]:
    def __init__(self, *types: ty.Type[T]):
        self.types: list[T]
        self.nullable: bool

    def __call__(self, obj: ty.Any) -> T: ...
    def is_contains_type(self, type_: ty.Type) -> bool: ...
    def __repr__(self) -> str: ...


def prepare_model(model: ty.Type) -> ModelSignature: ...


class FieldMod(Enum):
    UNIQUE: str

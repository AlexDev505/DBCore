from __future__ import annotations

import typing as ty
from abc import ABC, abstractmethod


class Operator(ABC):
    """
    Base operator that works with fields.
    """

    # SQL syntaxis
    sign: str

    @abstractmethod
    def get_values(self) -> ty.Sequence[ty.Any]:
        """
        :returns: values with which the fields are compared.
        """

    def __and__(self, other: Operator) -> AndOperator:
        return AndOperator(self, other)

    def __or__(self, other: Operator) -> OrOperator:
        return OrOperator(self, other)

    def __invert__(self) -> NotOperator:
        return NotOperator(self)

    @abstractmethod
    def __str__(self) -> str:
        """
        Renders operator to SQL code.
        """


class CmpOperator(Operator, ABC):
    """
    Base class for comparison operators.
    """

    def __init__(self, field_name: str, value: ty.Any):
        """
        :param field_name: The name of the field to compare.
        :param value: The value to compare.
        """
        self.field_name = field_name
        self.value = value

    def get_values(self) -> ty.Sequence[ty.Any]:
        return (self.value,)

    def __repr__(self):
        return f"{self.field_name} {self.sign} {{}}"

    __str__ = __repr__


class EqCmpOperator(CmpOperator):
    sign = "="


class NeCmpOperator(CmpOperator):
    sign = "!="


class LtCmpOperator(CmpOperator):
    sign = "<"


class LeCmpOperator(CmpOperator):
    sign = "<="


class GtCmpOperator(CmpOperator):
    sign = ">"


class GeCmpOperator(CmpOperator):
    sign = ">="


class ContainedCmpOperator(CmpOperator):
    sign = "IN"

    def get_values(self) -> ty.Sequence[ty.Any]:
        return tuple(self.value)

    def __repr__(self):
        return f"{self.field_name} {self.sign} ({', '.join(['{}'] * len(self.value))})"

    __str__ = __repr__


class IsNullCmpOperator(CmpOperator):
    sign = "IS NULL"

    def __init__(self, field_name: str, _: ty.Any):
        super().__init__(field_name, None)

    def get_values(self) -> ty.Sequence[ty.Any]:
        return tuple()

    def __repr__(self):
        return f"{self.field_name} {self.sign}"

    __str__ = __repr__


class LogicalOperator(Operator, ABC):
    """
    Base class for logical operators between two contained operators.
    """

    def __init__(
        self,
        first_operand: Operator,
        second_operand: Operator,
    ):
        self.first_operand = first_operand
        self.second_operand = second_operand

    def get_values(self) -> ty.Sequence[ty.Any]:
        return (
            *self.first_operand.get_values(),
            *self.second_operand.get_values(),
        )

    def __str__(self):
        return f"{self.first_operand!r} {self.sign} {self.second_operand!r}"

    def __repr__(self):
        return f"({str(self)})"


class AndOperator(LogicalOperator):
    sign = "AND"


class OrOperator(LogicalOperator):
    sign = "OR"


class NotOperator(Operator):
    sign = "NOT"

    def __init__(self, operand: Operator):
        self.operand = operand

    def get_values(self) -> ty.Sequence[ty.Any]:
        return self.operand.get_values()

    def __repr__(self):
        return f"{self.sign} ({self.operand})"

    __str__ = __repr__


class InvertedField:
    def __init__(self, field: str):
        self.field = field

    def __str__(self):
        return self.field

import typing as ty

from .models import ModelField
from .operators import ContainedCmpOperator


def contains(field, collection: ty.Sequence) -> ContainedCmpOperator:
    if not isinstance(field, ModelField):
        raise ValueError(f"first argument must be field of registered model")
    return field.contained(collection)  # noqa

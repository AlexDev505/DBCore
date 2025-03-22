import typing as ty

from .models import ModelField
from .operators import ContainedCmpOperator


def contains(
    field: ty.Annotated[ty.Any, ModelField], collection: ty.Sequence
) -> ContainedCmpOperator:
    if not isinstance(field, ModelField):
        raise ValueError(f"first argument must be field of registered model")
    return field.contained(collection)  # noqa


def group_by[T](
    field: ty.Annotated[ty.Any, ModelField], objs: list[T]
) -> dict[ty.Any, list[T]]:
    """
    Groups objects by field.
    :param field: field for group.
    :param objs: model instances.
    :returns: dict with keys - values of field and values - list of objects.
    """
    if not isinstance(field, ModelField):
        raise ValueError(f"first argument must be field of registered model")
    result = {}
    for obj in objs:
        if (value := getattr(obj, field.field.name)) not in result:
            result[value] = []
        result[value].append(obj)
    return result

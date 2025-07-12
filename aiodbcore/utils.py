import typing as ty

from .models import Field
from .operators import ContainedCmpOperator, IsNullCmpOperator


def contains[T](
    field: Field[T], collection: list[T] | tuple[T, ...]
) -> ContainedCmpOperator:
    if not isinstance(field, Field):
        raise ValueError("first argument must be field of registered model")
    return field.contained(collection)


def is_null(field: Field) -> IsNullCmpOperator:
    if not isinstance(field, Field):
        raise ValueError("first argument must be field of registered model")
    return field.is_null()


def group_by[FT, T: ty.Any | tuple](
    field: Field[FT], objs: list[T]
) -> dict[FT, list[T]]:
    """
    Groups objects by field.
    :param field: Field for a group.
    :param objs: Model instances.
    :returns: Dict with keys - values of field and values - list of objects.
    """
    if not isinstance(field, Field):
        raise ValueError("first argument must be field of registered model")
    result: dict[FT, list[T]] = {}
    i: int | None = None
    if isinstance(next(iter(objs), None), tuple):
        i = next(
            filter(
                lambda x: field.model_name == objs[0][x].__class__.__name__,
                range(len(objs[0])),
            )
        )
    for obj in objs:
        if (
            value := getattr(obj if i is None else obj[i], field.name)
        ) not in result:
            result[value] = []
        result[value].append(obj)
    return result

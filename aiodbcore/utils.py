import typing as ty

from .models import ModelField
from .operators import ContainedCmpOperator, IsNullCmpOperator


def contains(
    field: ty.Annotated[ty.Any, ModelField], collection: ty.Sequence
) -> ContainedCmpOperator:
    if not isinstance(field, ModelField):
        raise ValueError(f"first argument must be field of registered model")
    return field.contained(collection)  # noqa


def is_null(field: ty.Annotated[ty.Any, ModelField]) -> IsNullCmpOperator:
    if not isinstance(field, ModelField):
        raise ValueError(f"first argument must be field of registered model")
    return field.is_null()  # noqa


def group_by[T](field: ty.Annotated[ty.Any, ModelField], objs: T) -> dict[ty.Any, T]:
    """
    Groups objects by field.
    :param field: field for group.
    :param objs: model instances.
    :returns: dict with keys - values of field and values - list of objects.
    """
    if not isinstance(field, ModelField):
        raise ValueError(f"first argument must be field of registered model")
    if isinstance(objs[0], tuple):
        return _group_by_two_models(field, objs)
    return _group_by_one_model(field, objs)


def _group_by_one_model[T](
    field: ty.Annotated[ty.Any, ModelField], objs: list[T]
) -> dict[ty.Any, list[T]]:
    result = {}
    for obj in objs:
        if (value := getattr(obj, field.field.name)) not in result:
            result[value] = []
        result[value].append(obj)
    return result


def _group_by_two_models[T1, T2](
    field: ty.Annotated[ty.Any, ModelField], objs: list[tuple[T1, T2]]
) -> dict[ty.Any, list[tuple[T1, T2]]]:
    result = {}
    i = 0 if field.field.model_name == objs[0][0].__class__.__name__ else 1
    for obj in objs:
        if (value := getattr(obj[i], field.field.name)) not in result:
            result[value] = []
        result[value].append(obj)
    return result

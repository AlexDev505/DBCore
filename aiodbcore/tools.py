import hashlib
import typing as ty
from datetime import date, datetime, time


def watch_changes(_cls: ty.Type | None = None, hash_func=hashlib.md5):
    """
    watch_changes decorator allows you to detect
    changes in the attributes of an instances of class.

    It provides by saving hashes of attributes when instance created.
    Note: hashes will get from the string value of the attribute
        `hash_func(str(value).encode()).hexdigest()`

    >>> from dataclasses import dataclass, field
    >>> @watch_changes
    >>> @dataclass
    >>> class A:
    ...     a: int
    ...     b: dict
    >>> a = A(0, {"a": 0})
    >>> has_changes(a)
    False
    >>> a.a = 1
    >>> has_changes(a)
    True
    >>> a.a = 0
    >>> has_changes(a)
    False
    >>> a.b["a"] += 1
    >>> has_changes(a)
    True
    """

    def _decorator(cls):
        def init_hashes(obj: ty.Any, *args, **kwargs) -> None:
            getattr(obj, "__old_init__")(*args, **kwargs)
            hf = getattr(obj, "__wc_hash_func")
            hashes: dict[str, str] = {}
            for varname, value in obj.__dict__.items():
                if not varname.startswith("_"):
                    hashes[varname] = hf(str(value).encode()).hexdigest()
            setattr(obj, "__wc_hashes", hashes)

        setattr(cls, "__old_init__", cls.__init__)
        setattr(cls, "__wc_hash_func", hash_func)
        cls.__init__ = init_hashes

        return cls

    if _cls:
        return _decorator(_cls)
    return _decorator


def is_watch_changes_setup(obj: ty.Any) -> bool:
    """
    :param obj: instance of any class.
    :return: `True` if `obj` class wrapped by `watch_changes`, `False` otherwise.
    """
    hashes = getattr(obj, "__wc_hashes", None)
    hash_func = getattr(obj, "__wc_hash_func", None)
    return hashes is not None and hash_func is not None


def has_changes(obj: ty.Any) -> bool:
    """
    :param obj: instance of class that wrapped by `watch_changes`.
    :return: `True` if `obj` attributes has changed, `False` otherwise.
    """
    hashes = getattr(obj, "__wc_hashes", None)
    hash_func = getattr(obj, "__wc_hash_func", None)
    if hashes is None or hash_func is None:
        raise ValueError(f"{obj} is not `watch_changes` object")

    return any(
        hashes.get(varname, None) != hash_func(str(value).encode()).hexdigest()
        for varname, value in obj.__dict__.items()
        if not varname.startswith("_")
    )


def get_changed_attributes(obj: ty.Any) -> tuple[str, ...]:
    """
    :param obj: instance of class that wrapped by `watch_changes`.
    :returns: names of attributes that have changed.
    """
    hashes = getattr(obj, "__wc_hashes", None)
    hash_func = getattr(obj, "__wc_hash_func", None)
    if hashes is None or hash_func is None:
        raise ValueError(f"{obj} is not `watch_changes` object")

    return tuple(
        varname
        for varname, value in obj.__dict__.items()
        if (
            not varname.startswith("_")
            and hashes.get(varname, None)
            != hash_func(str(value).encode()).hexdigest()
        )
    )


class Construct[T](ty.Protocol):
    def __call__(self, *args, **kwargs) -> T: ...


class DTConstruct[T](ty.Protocol):
    def fromisoformat(self, value: str) -> T: ...


def is_dt_type(obj: ty.Any) -> ty.TypeGuard[DTConstruct]:
    return obj in {datetime, date, time}

import typing as ty


class DBError(Exception):
    msg: str = ""

    def __init__(
        self,
        query: str,
        args: ty.Sequence[ty.Any],
        base_exc: Exception,
        msg: str | None = None,
        **extra: ty.Any,
    ):
        self.query = query
        self.args = args
        self.base_exc = base_exc
        self.extra = extra
        self.msg = (msg or self.msg).format(**self.extra)

    def __str__(self) -> str:
        return (
            f"{self.msg} on query {self.query} with args {self.args}."
            f" Base exc {type(self.base_exc).__name__}: {self.base_exc}"
        )


class UniqueRequiredError(DBError):
    msg: str = "Value for field `{field_name}` must be unique."

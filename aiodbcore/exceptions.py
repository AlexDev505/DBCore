import typing as ty


class DBError(Exception):
    msg: str = ""

    def __init__(
        self,
        msg: str | None = None,
        base_exc: Exception | None = None,
        **extra: ty.Any,
    ):
        self.base_exc = base_exc
        self.extra = extra
        self.msg = (msg or self.msg).format(**self.extra)

    def __str__(self) -> str:
        exc_msg = (
            f" Base exc {type(self.base_exc).__name__}: {self.base_exc}"
            if self.base_exc
            else ""
        )
        return f"{self.msg}{exc_msg}"


class QueryError(DBError):
    def __init__(
        self,
        query: str,
        params: ty.Sequence[ty.Any],
        base_exc: Exception,
        msg: str | None = None,
        **extra: ty.Any,
    ):
        msg = (msg or self.msg) + " on query `{query}` with args {params}."
        extra.update(dict(query=query, params=params))
        super().__init__(msg, base_exc, **extra)


class UniqueRequiredError(QueryError):
    msg = "Value for field `{field_name}` must be unique."


class ConnectionIsNotAccrued(DBError):
    msg = "Connection is not accrued"

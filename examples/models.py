from dataclasses import dataclass


@dataclass
class User:
    id: int | None = None
    name: str = ""
    age: int = 0
    moneys: int = 1000


@dataclass
class Chat:
    id: int | None = None
    title: str = ""

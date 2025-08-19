# DBCore [![Python 3.12+](https://badgen.net/badge/Python/3.12+/blue)](https://www.python.org/downloads/) [![License:MIT](https://badgen.net/badge/License/MIT/blue)](https://github.com/AlexDev505/DBCore/blob/master/LICENSE.txt) [![PyPi version](https://img.shields.io/pypi/v/aiodbcore.svg)](https://pypi.python.org/pypi/aiodbcore/)

ORM that does not require the developer to create models specifically for it.
dbcore works with dataclasses and allows you to connect from one interface
to both local databases (sqlite+aiosqlite) and remote databases (postgres+asyncpg).

### Small example

```python
import os
import asyncio
from dataclasses import dataclass

from aiodbcore import AsyncDBCore


# a model in which only the id field gives out DB membership
@dataclass
class MyModel:
    id: int | None = None
    foo: int = 0
    bar: str = ""


class MyDB(AsyncDBCore[MyModel]):
    # there i can implement my queries
    async def my_simple_query(self) -> list[MyModel]:
        return await self.fetchall(MyModel, where=MyModel.foo > 10)


async def main():
    MyDB.init(os.environ["DB"])  # init db at start of program
    db = MyDB()
    data = await db.my_simple_query()
    first = data[0]
    first.foo += 100
    await db.save(first)
    await db.close_connections()


if __name__ == '__main__':
    asyncio.run(main())

```

The declaration of the model from the example above is certainly simple and elegant, but this method does not allow the IDE to show type hints, and static typers will complain. Therefore, there is another way to declare models, it will require minimal changes in the code.

```python
from dataclasses import dataclas
from aiodbcore.models import Field

@dataclass
class MyModel:
    # Here you can wrap default values in `Field`
    # if you don't want complaints from static typers,
    # but it is not necessary
    id: Field[int | None] = Field(None)
    foo: Field[int] = 0
    bar: Filed[str] = ""
```

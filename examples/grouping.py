from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, time, timedelta

from aiodbcore import AsyncDBCore, utils


DB_PATH = "sqlite+aiosqlite://:memory:"


@dataclass
class Slot:
    id: int | None = None
    date: date = 0
    time: time = 0
    occupied: bool = False


class DB(AsyncDBCore[Slot]):
    pass


async def main():
    DB.init(DB_PATH)
    db = DB()

    await db.create_tables()

    default_times = [time(9, 00), time(11, 30), time(14, 30), time(17, 00)]
    d = date.today()

    for i in range(5):
        d += timedelta(days=i)
        for t in default_times:
            await db.insert(Slot(date=d, time=t))

    # Groups result by `date` field
    slots: dict[date, list[Slot]] = utils.group_by(Slot.date, await db.fetchall(Slot))
    for d, slots in slots.items():
        print(d, *slots, sep="\n")
        print()

    await db.drop_table(Slot)
    await db.close_connections()


asyncio.run(main())

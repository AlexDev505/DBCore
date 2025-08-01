from __future__ import annotations

import asyncio
import random
import sys
from dataclasses import dataclass
from datetime import date, time, timedelta

sys.path.append("..")

from aiodbcore import AsyncDBCore, utils
from aiodbcore.joins import InnerJoin, LeftJoin
from aiodbcore.models import Field

DB_PATH = "sqlite+aiosqlite://:memory:"


@dataclass
class Slot:
    id: Field[int | None] = Field(None)
    date: Field[date] = Field(date.today())
    time: Field[time] = Field(time())
    occupied: Field[bool] = Field(False)


@dataclass
class Booking:
    id: Field[int | None] = Field(None)
    slot_id: Field[int | None] = Field(None)


class DB(AsyncDBCore[Slot | Booking]):
    pass


async def main():
    DB.init(DB_PATH)
    db = DB()

    await db.create_tables()

    default_times = [time(9, 00), time(11, 30), time(14, 30), time(17, 00)]
    d = date.today()

    # creating slots on two days
    for _ in range(2):
        for t in default_times:
            await db.insert(Slot(date=d, time=t))
        d += timedelta(days=1)
    # creating 5 bookings with random slots
    slots = random.sample(await db.fetchall(Slot), 5)
    for slot in slots:
        await db.insert(Booking(slot_id=slot.id))
    # marks this slots as occupied
    await db.update(
        Slot,
        {Slot.occupied: True},
        where=utils.contains(Slot.id, [slot.id for slot in slots]),
        # where=Slot.id.contained([slot.id for slot in slots]),  # It`s same
    )

    # gets all slots and groups by `date` field
    # slots: dict[date, list[Slot]]
    slots = utils.group_by(Slot.date, await db.fetchall(Slot))
    print("all slots grouped by `date`:")
    for d, slots in slots.items():
        print(d, *slots, sep="\n")
    print()

    bookings_with_slots = await db.fetchall(
        Booking,
        join=InnerJoin(Slot, (Booking.slot_id, Slot.id)),
        where=Slot.date == date.today(),
    )
    print("Today bookings:", *bookings_with_slots, sep="\n")
    print()

    slots_with_bookings = await db.fetchall(
        Slot,
        join=LeftJoin(Booking, (Booking.slot_id, Slot.id)),
        # Order by date and time in descending order
        order_by=(Slot.date, ~Slot.time),
    )
    print("All slots:", *slots_with_bookings, sep="\n")
    print()

    slots_without_bookings = await db.fetchall(
        Slot,
        join=LeftJoin(Booking, (Booking.slot_id, Slot.id)),
        where=utils.is_null(Booking.id),
        # where=Booking.id.is_null()  # It`s same,
    )
    slots = utils.group_by(Slot.date, slots_without_bookings)
    print("Slots without bookings grouped by `date`:")
    for d, slots in slots.items():
        print(d, *slots, sep="\n")

    await db.drop_table(Slot)
    await db.drop_table(Booking)
    await db.close_connections()


asyncio.run(main())

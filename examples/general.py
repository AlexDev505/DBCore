import asyncio
import sys

sys.path.append("..")
from models import Chat, User

from aiodbcore import AsyncDBCore

DB_PATH = "sqlite+aiosqlite://:memory:"


class DB(AsyncDBCore[User | Chat]):
    async def get_old_peoples(self) -> list[User]:
        return await self.fetchall(User, where=User.age >= 20)


async def main():
    DB.init(DB_PATH)
    db = DB()
    await db.create_tables()  # Creates all tables

    # insert some data in db
    await db.insert([User(name="Stas", age=21), User(name="Alex", age=20)])
    zahar = await db.insert(User(name="Zahar", age=15))
    await db.insert(Chat(title="726 room"))

    # fetching data
    old_peoples = await db.get_old_peoples()
    chat = await db.fetchone(Chat, where=Chat.title == "726 room")
    print(f"Zahar id: {zahar.id}")
    print("old peoples:", *old_peoples, sep="\n")
    print(f"chat: {chat}")

    # updating data
    await db.update(
        User,
        {User.moneys: User.moneys + 1500},
        where=User.age.contained((20, 21)),
    )  # where User.age IN (20, 21)
    print("new moneys:", *(await db.fetchall(User)), sep="\n")
    # update one instance and save it
    zahar.moneys += 1000
    await db.save(zahar)
    print("zahar changed:", await db.fetchone(User, where=User.id == zahar.id))

    # deleting rows
    await db.delete(User, where=User.age > 20)
    print("after deletion:", *await db.fetchall(User), sep="\n")

    # dropping tables
    await db.drop_table(User)
    await db.drop_table(Chat)

    await DB.close_connections()


if __name__ == "__main__":
    asyncio.run(main())

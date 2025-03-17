import asyncio

from aiodbcore import AsyncDBCore
from aiodbcore.utils import contains
from models import User, Chat


DB_PATH = "sqlite+aiosqlite://:memory:"
DB_PATH = "postgresql+asyncpg://test_db_kwlq_user:3ZzP0k8cPUo0EYd1Y4Cnt1TTGz1g3iEp@dpg-cv63pufnoe9s73bqmj30-a.ohio-postgres.render.com/test_db_kwlq"


class DB(AsyncDBCore[User | Chat]):
    async def get_old_peoples(self) -> list[User]:
        return await self.fetchall(User, where=User.age >= 20)


async def main():
    DB.init(DB_PATH)
    db = DB()
    await db.create_tables()  # Creates all tables

    # insert some data in db
    await db.insert(User(name="Stas", age=21))
    await db.insert(User(name="Alex", age=20))
    zahar = await db.insert(User(name="Zahar", age=15))
    await db.insert(Chat(title="726 room"))

    # fetching data
    old_peoples = await db.get_old_peoples()
    chat = await db.fetchone(Chat, where=Chat.title == "726 room")
    print(f"Zahar id: {zahar.id}")
    print("old peoples:", *old_peoples, sep="\n")
    print(f"chat: {chat}")

    # updating data
    await db.update(User, {User.moneys: 1500}, where=contains(User.age, (20, 21)))
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

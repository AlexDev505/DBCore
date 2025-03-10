import asyncio

from models import Chat
from aiodbcore import AsyncDBCore


SQLITE_DB_PATH = "sqlite+aiosqlite://:memory:"
POSTGRES_DB_PATH = "postgresql+asyncpg://user:pass@host/db"


class DB(AsyncDBCore[Chat]):
    pass


async def main():
    DB.init(SQLITE_DB_PATH, db_name="sqlite_db")
    DB.init(POSTGRES_DB_PATH, db_name="postgres_db")

    sqlite_db = DB("sqlite_db")
    postgres_db = DB("postgres_db")

    await sqlite_db.create_tables()
    await postgres_db.create_tables()

    # insert some data in local db
    await sqlite_db.insert(Chat(title="first"))
    await sqlite_db.insert(Chat(title="second"))

    # copy all chats from local db to remote db
    chats = await sqlite_db.fetchall(Chat)
    for chat in chats:
        await postgres_db.insert(chat)

    await sqlite_db.drop_table(Chat)
    await postgres_db.drop_table(Chat)

    # closing all db connections
    await DB.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
